import psutil

def get_active_connections(ports):
    connections = []
    
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr and conn.raddr and conn.status == "ESTABLISHED":
            if conn.laddr.port in ports:
                connections.append(conn.raddr.ip)  # Speichert die Client-IP-Adresse
    
    return {"count": len(connections), "clients": connections}

def get_connection_info():
    return {
        "ssh": get_active_connections({22}),  # SSH (Port 22)
        "smb": get_active_connections({445, 139})  # SMB (Ports 445 & 139)
    }

# Beispielaufruf
print(get_connection_info())
