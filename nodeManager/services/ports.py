import socket

from ..models import NodeApp, NodeManagerSettings


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) != 0


def find_free_port(settings_obj=None):
    settings_obj = settings_obj or NodeManagerSettings.current()
    used_ports = set(NodeApp.objects.exclude(status=NodeApp.STATUS_DELETED).values_list("port", flat=True))
    for port in range(settings_obj.port_range_start, settings_obj.port_range_end + 1):
        if port not in used_ports and is_port_available(port):
            return port
    raise RuntimeError("No available Node.js internal ports in configured range.")


def reserve_port(settings_obj=None):
    return find_free_port(settings_obj)


def release_port(port):
    return True
