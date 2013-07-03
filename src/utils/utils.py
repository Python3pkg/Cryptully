import os
import sys

from time import localtime
from time import strftime


def doServerHandshake(sock):
    # Send the server's public key
    localPubKey = sock.crypto.getLocalPubKeyAsString()
    sock.send(localPubKey)

    # Receive the client's public key
    remotePubKey = sock.recv()
    sock.crypto.setRemotePubKey(remotePubKey)

    # Switch to RSA encryption to exchange the AES key, IV, and salt
    sock.setEncryptionType(sock.RSA)

    # Send the AES key, IV, and salt
    sock.send(sock.crypto.aesKey)
    sock.send(sock.crypto.aesIv)
    sock.send(sock.crypto.aesSalt)

    # Switch to AES encryption for the remainder of the connection
    sock.setEncryptionType(sock.AES)


def doClientHandshake(sock):
    # Receive the server's public key
    remotePubKey = sock.recv()
    sock.crypto.setRemotePubKey(remotePubKey)

    # Send the client's public key
    localPubKey = sock.crypto.getLocalPubKeyAsString()
    sock.send(localPubKey)

    # Switch to RSA encryption to receive the AES key, IV, and salt
    sock.setEncryptionType(sock.RSA)

    # Receive the AES key, IV, and salt
    sock.crypto.aesKey  = sock.recv()
    sock.crypto.aesIv   = sock.recv()
    sock.crypto.aesSalt = sock.recv()

    # Switch to AES encryption for the remainder of the connection
    sock.setEncryptionType(sock.AES)


def saveKeypair(crypto, passphrase):
    # Cast passphrase to a stringto avoid any strange types
    passphrase = str(passphrase)

    storeDir = os.path.join(os.path.expanduser('~'), '.cryptully')

    # Create the path if it doesn't already exist
    if not os.path.exists(storeDir):
        os.makedirs(storeDir)

    keypairFile = os.path.join(storeDir, 'keypair.pem')

    crypto.writeLocalKeypairToFile(keypairFile, passphrase)

    # Set the directory & keypair permissions to read/write/execute for the current user only
    # and no permissions for everyone else
    os.chmod(storeDir, 0700)
    os.chmod(keypairFile, 0700)


def doesSavedKeypairExist():
    storeDir = os.path.join(os.path.expanduser('~'), '.cryptully')
    return os.path.exists(storeDir)


def clearKeypair():
    storeDir = os.path.join(os.path.expanduser('~'), '.cryptully')

    # Check that the path exists
    if not os.path.exists(storeDir):
        return

    keypairFile = os.path.join(storeDir, 'keypair.pem')
    os.unlink(keypairFile)

    # Try to remove the directory if empty
    os.rmdir(storeDir)


def loadKeypair(crypto, passphrase):
    # Cast passphrase to a stringto avoid any strange types
    passphrase = str(passphrase)

    storeDir = os.path.join(os.path.expanduser('~'), '.cryptully')
    keypairFile = os.path.join(storeDir, 'keypair.pem')

    # Check that the path and keypair file both exist
    if not (os.path.exists(storeDir) and os.path.exists(keypairFile)):
        return

    crypto.readLocalKeypairFromFile(keypairFile, passphrase)


def doesSavedKeypairExist():
    storeDir = os.path.join(os.path.expanduser('~'), '.cryptully')
    keypairFile = os.path.join(storeDir, 'keypair.pem')

    # Check that the path and keypair file both exist
    return (os.path.exists(storeDir) and os.path.exists(keypairFile))


def getTimestamp():
    return strftime('%H:%M:%S', localtime()) + ': '


def getAbosluteResourcePath(relativePath):
    try:
        # PyInstaller stores data files in a tmp folder refered to as _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath('.')
        # If the resource does not exist in the current directory, try the src directory
        # This should only apply to running the application non-packaged
        if not os.path.exists(os.path.join(basePath, relativePath)):
            relativePath = 'src/' + relativePath

    return os.path.join(basePath, relativePath)