import os
import M2Crypto

from utils import constants
from utils import exceptions

class Crypto(object):
    ENCRYPT = 1;
    DECRYPT = 0;

    dhPrime = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
    dhGenerator= 5

    def __init__(self):
        self.localKeypair  = None
        self.remoteKeypair = None
        self.aesKey        = None
        self.aesIv         = None
        self.aesSalt       = None
        self.dh            = None
        self.aesMode       = constants.DEFAULT_AES_MODE


    def generateKeys(self, rsaBits=2048, aesMode=constants.DEFAULT_AES_MODE):
        self.generateRSAKeypair(rsaBits)
        self.generateAESKey(aesMode)


    def generateRSAKeypair(self, bits=2048):
        # Generate the keypair (65537 as the public exponent)
        self.localKeypair = M2Crypto.RSA.gen_key(bits, 65537, self.__generateKeypairCallback)


    def generateAESKey(self, aesMode=constants.DEFAULT_AES_MODE):
        self.aesMode = aesMode

        # Generate the AES key and IV
        bitsString = aesMode[4:7]
        if bitsString == '128':
            self.aesBytes = 16
        elif bitsString == '192':
            self.aesBytes = 24
        elif bitsString == '256':
            self.aesBytes = 32
        else:
            raise exceptions.CryptoError("Invalid AES mode")

        self.aesKey  = M2Crypto.Rand.rand_bytes(self.aesBytes)
        self.aesIv   = M2Crypto.Rand.rand_bytes(self.aesBytes)
        self.aesSalt = M2Crypto.Rand.rand_bytes(8)


    def generateDHKey(self):
        self.dh = M2Crypto.DH.set_params(decToMpi(self.dhPrime), decToMpi(self.dhGenerator))
        self.dh.gen_key()


    def computeDHSecret(self, publicKey):
        self.dhSecret = binToDec(self.dh.compute_key(decToMpi(publicKey)))
        hash = self.hash(str(self.dhSecret), 'sha512')
        self.aesKey = hash[0:32]
        self.aesIv = hash[32:64]
        self.aesSalt = hash[56:64]


    def setRemotePubKey(self, pubKey):
        if type(pubKey) is str:
            bio = M2Crypto.BIO.MemoryBuffer(pubKey)
            self.remoteKeypair = M2Crypto.RSA.load_pub_key_bio(bio)
        elif type(pubKey) is M2Crypto.RSA:
            self.remoteKeypair = pubKey
        else:
            raise exceptions.CryptoError("Public key is not a string or RSA key object.")


    def rsaEncrypt(self, message):
        self.__checkRemoteKeypair()
        try:
            return self.remoteKeypair.public_encrypt(message, M2Crypto.RSA.pkcs1_oaep_padding)
        except M2Crypto.RSA.RSAError as rsae:
            raise exceptions.CryptoError(str(rsae))


    def rsaDecrypt(self, message):
        self.__checkLocalKeypair()
        try:
            return self.localKeypair.private_decrypt(message, M2Crypto.RSA.pkcs1_oaep_padding)
        except M2Crypto.RSA.RSAError as rsae:
            raise exceptions.CryptoError(str(rsae))


    def aesEncrypt(self, message):
        try:
            cipher = self.__aesGetCipher(self.ENCRYPT)
            encMessage = cipher.update(message)
            return encMessage + cipher.final()
        except M2Crypto.EVP.EVPError as evpe:
            raise exceptions.CryptoError(str(evpe))


    def aesDecrypt(self, message):
        try:
            cipher = self.__aesGetCipher(self.DECRYPT)
            decMessage = cipher.update(message)
            return decMessage + cipher.final()
        except M2Crypto.EVP.EVPError as evpe:
            raise exceptions.CryptoError(str(evpe))


    def __aesGetCipher(self, op):
        return M2Crypto.EVP.Cipher(alg=self.aesMode, key=self.aesKey, iv=self.aesIv, salt=self.aesSalt, d='sha256', op=op)


    def generateHmac(self, message):
        hmac = M2Crypto.EVP.HMAC(self.aesKey, 'sha256')
        hmac.update(message)
        return hmac.digest()


    def hash(self, message, type='sha256'):
        hash = M2Crypto.EVP.MessageDigest(type)
        hash.update(message)
        return hash.final()


    def stringHash(self, message):
        digest = self.hash(message)
        return hex(self.__octx_to_num(digest))[2:-1].upper()


    def readLocalKeypairFromFile(self, file, passphrase):
        self._keypairPassphrase = passphrase
        try:
            self.localKeypair = M2Crypto.RSA.load_key(file, self.__passphraseCallback)
        except M2Crypto.RSA.RSAError as rsae:
            raise exceptions.CryptoError(str(rsae))


    def readRemotePubKeyFromFile(self, file):
        self.remoteKeypair = M2Crypto.RSA.load_pub_key(file)


    def writeLocalKeypairToFile(self, file, passphrase):
        self.__checkLocalKeypair()
        self._keypairPassphrase = passphrase
        self.localKeypair.save_key(file, self.aesMode, self.__passphraseCallback)


    def writeLocalPubKeyToFile(self, file):
        self.__checkLocalKeypair()
        self.localKeypair.save_pub_key(file)


    def writeRemotePubKeyToFile(self, file):
        self.__checkRemoteKeypair()
        self.remoteKeypair.save_pub_key(file)


    def getLocalPubKeyAsString(self):
        self.__checkLocalKeypair()
        bio = M2Crypto.BIO.MemoryBuffer()
        self.localKeypair.save_pub_key_bio(bio)
        return bio.read()


    def getRemotePubKeyAsString(self):
        self.__checkRemoteKeypair()
        bio = M2Crypto.BIO.MemoryBuffer()
        self.remoteKeypair.save_pub_key_bio(bio)
        return bio.read()


    def getKeypairAsString(self, passphrase):
        self._keypairPassphrase = passphrase
        return self.localKeypair.as_pem(self.aesMode, self.__passphraseCallback)


    def getLocalFingerprint(self):
        self.__checkLocalKeypair()
        return self.__generateFingerprint(self.getLocalPubKeyAsString())


    def getRemoteFingerprint(self):
        self.__checkRemoteKeypair()
        return self.__generateFingerprint(self.getRemotePubKeyAsString())


    def __generateFingerprint(self, key):
        digest = self.stringHash(key)

        # Add colons between every 2 characters of the fingerprint
        fingerprint = ''
        digestLength = len(digest)
        for i in range(0, digestLength):
            fingerprint += digest[i]
            if i&1 and i != 0 and i != digestLength-1:
                fingerprint += ':'
        return fingerprint


    def __octx_to_num(self, data):
        converted = 0L
        length = len(data)
        for i in range(length):
            converted = converted + ord(data[i]) * (256L ** (length - i - 1))
        return converted


    def getDHPubKey(self):
        return mpiToDec(self.dh.pub)


    def __checkLocalKeypair(self):
        if self.localKeypair is None:
            raise exceptions.CryptoError("Local keypair not set.")


    def __checkRemoteKeypair(self):
        if self.remoteKeypair is None:
            raise exceptions.CryptoError("Remote public key not set.")


    def __generateKeypairCallback(self):
        pass


    def __passphraseCallback(self, ignore, prompt1=None, prompt2=None):
        return self._keypairPassphrase


def mpiToDec(mpi): 
    bn = M2Crypto.m2.mpi_to_bn(mpi)
    hex = M2Crypto.m2.bn_to_hex(bn)
    return int(hex, 16)


def binToDec(binval):
    bn = M2Crypto.m2.bin_to_bn(binval)
    hex = M2Crypto.m2.bn_to_hex(bn)
    return int(hex, 16)


def decToMpi(dec):
    bn = M2Crypto.m2.dec_to_bn('%s' % dec)
    return M2Crypto.m2.bn_to_mpi(bn)
