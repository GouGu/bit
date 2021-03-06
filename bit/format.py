from bit.base58 import b58decode_check, b58encode_check
from bit.crypto import (
    decode_dss_signature, ripemd160_sha256, verify_signature
)
from bit.curve import GROUP_ORDER, x_to_y
from bit.exceptions import InvalidSignature
from bit.utils import bytes_to_hex, hex_to_bytes, int_to_unknown_bytes

MAIN_PUBKEY_HASH = b'\x00'
MAIN_SCRIPT_HASH = b'\x05'
MAIN_PRIVATE_KEY = b'\x80'
MAIN_BIP32_PUBKEY = b'\x04\x88\xb2\x1e'
MAIN_BIP32_PRIVKEY = b'\x04\x88\xad\xe4'
TEST_PUBKEY_HASH = b'\x6f'
TEST_SCRIPT_HASH = b'\xc4'
TEST_PRIVATE_KEY = b'\xef'
TEST_BIP32_PUBKEY = b'\x045\x87\xcf'
TEST_BIP32_PRIVKEY = b'\x045\x83\x94'
PUBLIC_KEY_UNCOMPRESSED = b'\x04'
PUBLIC_KEY_COMPRESSED_EVEN_Y = b'\x02'
PUBLIC_KEY_COMPRESSED_ODD_Y = b'\x03'
PRIVATE_KEY_COMPRESSED_PUBKEY = b'\x01'


def verify_sig(signature, data, public_key, strict=False):
    """Verifies some data was signed by the owner of a public key.

    :param signature: The signature to verify.
    :type signature: ``bytes``
    :param data: The data that was supposedly signed.
    :type data: ``bytes``
    :param public_key: The public key.
    :type public_key: ``bytes``
    :param strict: Whether or not to check for BIP-62 compliance.
    :type strict: ``bool``
    :raises InvalidSignature: If any checks fail.
    :returns: ``True`` if all checks pass.
    """
    if strict:  # pragma: no cover
        _, s = decode_dss_signature(signature)
        if s > GROUP_ORDER // 2:
            raise InvalidSignature('High S')

    return verify_signature(signature, data, public_key_to_coords(public_key))


def make_compliant_sig(signature):
    """Adhere to BIP-62:
    https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki
    """

    r, s = decode_dss_signature(signature)
    s = GROUP_ORDER - s if s > GROUP_ORDER // 2 else s

    r = int_to_unknown_bytes(r)
    s = int_to_unknown_bytes(s)

    if r[0] & 0x80:
        r = b'\x00' + r

    if s[0] & 0x80:
        s = b'\x00' + s

    r = b'\x02' + int_to_unknown_bytes(len(r)) + r
    s = b'\x02' + int_to_unknown_bytes(len(s)) + s

    return b'\x30' + int_to_unknown_bytes(len(r) + len(s)) + r + s


def address_to_public_key_hash(address):
    return b58decode_check(address)[1:]


def hex_to_wif(private_key, version='main', compressed=False):

    if version == 'test':
        prefix = TEST_PRIVATE_KEY
    else:
        prefix = MAIN_PRIVATE_KEY

    if compressed:
        suffix = PRIVATE_KEY_COMPRESSED_PUBKEY
    else:
        suffix = b''

    if not isinstance(private_key, bytes):
        private_key = hex_to_bytes(private_key)

    private_key = prefix + private_key + suffix

    return b58encode_check(private_key)


def wif_to_hex(wif):

    private_key = b58decode_check(wif)

    version = private_key[:1]

    if version == MAIN_PRIVATE_KEY:
        version = 'main'
    elif version == TEST_PRIVATE_KEY:
        version = 'test'
    else:
        raise ValueError('{} does not correspond to a mainnet nor '
                         'testnet address.'.format(private_key[:1]))

    # Remove version byte and, if present, compression flag.
    if len(wif) == 52 and private_key[-1] == 1:
        private_key, compressed = private_key[1:-1], True
    else:
        private_key, compressed = private_key[1:], False

    return bytes_to_hex(private_key), compressed, version


def wif_checksum_check(wif):

    try:
        decoded = b58decode_check(wif)
    except ValueError:
        return False

    if decoded[:1] in (MAIN_PRIVATE_KEY, TEST_PRIVATE_KEY):
        return True

    return False


def public_key_to_address(public_key, version='main'):

    if version == 'test':
        version = TEST_PUBKEY_HASH
    else:
        version = MAIN_PUBKEY_HASH

    length = len(public_key)

    if length not in (33, 65):
        raise ValueError('{} is an invalid length for a public key.'.format(length))

    return b58encode_check(version + ripemd160_sha256(public_key))


def public_key_to_coords(public_key):

    length = len(public_key)

    if length == 33:
        flag, x = int.from_bytes(public_key[:1], 'big'), int.from_bytes(public_key[1:], 'big')
        y = x_to_y(x, flag & 1)
    elif length == 65:
        x, y = int.from_bytes(public_key[1:33], 'big'), int.from_bytes(public_key[33:], 'big')
    else:
        raise ValueError('{} is an invalid length for a public key.'.format(length))

    return x, y


def coords_to_public_key(x, y, compressed=True):

    if compressed:
        y = PUBLIC_KEY_COMPRESSED_ODD_Y if y & 1 else PUBLIC_KEY_COMPRESSED_EVEN_Y
        return y + x.to_bytes(32, 'big')

    return PUBLIC_KEY_UNCOMPRESSED + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')


def point_to_public_key(point, compressed=True):
    return coords_to_public_key(point.x, point.y, compressed)
