
def to_variable_length(n):
    out = []
    first = True
    while n > 0 or first:
        tmp = n & 0x7F
        n >>= 7
        if first:
            tmp |= 0x00
        else:
            tmp |= 0x80
        out.append(tmp)
        first = False
    out.reverse()
    return bytes(out)

def to_bytes(n, l=4):
    out = b""
    first = True
    while n > 0 or first:
        out = bytes([n % 256]) + out
        n = int(n / 256)
        first = False

    out = (b"\x00" * (l - len(out))) + out
    return out


