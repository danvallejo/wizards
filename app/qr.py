import socket

import qrcode
import qrcode.image.svg


def qr_svg(url: str) -> str:
    """Inline SVG QR code for url (no Pillow needed)."""
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
    svg: str = image.to_string(encoding="unicode")
    return svg


def detect_lan_ip() -> str:
    """This machine's LAN IPv4, so phones on the same network can open the QR link.

    A UDP connect() only picks the outbound interface; no packet is sent.
    ponytail: picks the default-route interface; wrong on some VPN/Docker setups,
    where BASE_URL should be set explicitly.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 80))  # TEST-NET-1, never routed to anyone
            return str(s.getsockname()[0])
    except OSError:
        return "127.0.0.1"
