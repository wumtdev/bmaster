from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta
import ipaddress
import socket

def get_local_ips():
    """Get all local IP addresses"""
    ips = []
    
    # Get hostname and its IP
    hostname = socket.gethostname()
    try:
        host_ip = socket.gethostbyname(hostname)
        ips.append(host_ip)
    except:
        pass
    
    # Get all network interfaces
    try:
        # This gets all addresses for the current hostname
        addr_info = socket.getaddrinfo(hostname, None)
        for info in addr_info:
            ip = info[4][0]
            # Filter out IPv6 link-local and only keep IPv4 for simplicity
            # Remove the next two lines if you want IPv6 too
            if ':' not in ip:  # Simple IPv4 check
                if ip not in ips:
                    ips.append(ip)
    except:
        pass
    
    # Always include localhost
    if '127.0.0.1' not in ips:
        ips.append('127.0.0.1')
    
    return ips

def get_hostnames():
    """Get hostname and FQDN"""
    names = []
    
    # Get hostname
    hostname = socket.gethostname()
    names.append(hostname)
    
    # Get FQDN
    try:
        fqdn = socket.getfqdn()
        if fqdn != hostname and fqdn not in names:
            names.append(fqdn)
    except:
        pass
    
    # Always include localhost
    if 'localhost' not in names:
        names.append('localhost')
    
    return names

def generate_auto_self_signed_cert(days_valid=365, extra_ips=None, extra_dns=None):
    """
    Generate self-signed certificate with auto-detected network info
    
    Args:
        days_valid: Certificate validity period
        extra_ips: Additional IP addresses to include (list of strings)
        extra_dns: Additional DNS names to include (list of strings)
    
    Returns:
        tuple: (private_key_pem, cert_der, fingerprint_hex, cert_info)
    """
    
    # Auto-detect network information
    ip_addresses = get_local_ips()
    dns_names = get_hostnames()
    
    # Add any extra IPs/DNS names provided
    if extra_ips:
        ip_addresses.extend([ip for ip in extra_ips if ip not in ip_addresses])
    if extra_dns:
        dns_names.extend([name for name in extra_dns if name not in dns_names])
    
    # Use first DNS name or first IP as Common Name
    common_name = dns_names[0] if dns_names else ip_addresses[0]
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    
    # Minimal subject/issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    # Build certificate
    cert_builder = x509.CertificateBuilder() \
        .subject_name(subject) \
        .issuer_name(issuer) \
        .public_key(private_key.public_key()) \
        .serial_number(x509.random_serial_number()) \
        .not_valid_before(datetime.utcnow()) \
        .not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
    
    # Build SAN list
    san_list = []
    for dns_name in dns_names:
        san_list.append(x509.DNSName(dns_name))
    for ip in ip_addresses:
        try:
            san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))
        except ValueError:
            # Skip invalid IPs
            pass
    
    cert_builder = cert_builder.add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    )
    
    # Basic constraints - mark as CA
    cert_builder = cert_builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=0),
        critical=True,
    )
    
    # Sign certificate
    certificate = cert_builder.sign(private_key, hashes.SHA256())
    
    # Serialize
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    cert_der = certificate.public_bytes(serialization.Encoding.PEM)
    fingerprint = certificate.fingerprint(hashes.SHA256())
    fingerprint_hex = ":".join([f"{b:02X}" for b in fingerprint])
    
    # Prepare info dict
    cert_info = {
        'common_name': common_name,
        'ip_addresses': ip_addresses,
        'dns_names': dns_names,
        'valid_days': days_valid,
        'fingerprint': fingerprint_hex
    }
    
    return private_key_pem, cert_der, fingerprint_hex, cert_info


# Simple usage - fully automatic
def setup_cert(key_path, cert_path):
    print("Generating self-signed certificate...")
    print("Auto-detecting network configuration...\n")
    
    # Generate with auto-detection
    private_key, cert_der, fingerprint, info = generate_auto_self_signed_cert(
        days_valid=365 * 10,
    )
    
    # Save files
    with open(key_path, "wb") as f:
        f.write(private_key)
    
    with open(cert_path, "wb") as f:
        f.write(cert_der)
    
    # Print certificate info
    print("Certificate generated successfully!")
    print(f"\nCommon Name: {info['common_name']}")
    print(f"\nIP Addresses included:")
    for ip in info['ip_addresses']:
        print(f"  - {ip}")
    print(f"\nDNS Names included:")
    for dns in info['dns_names']:
        print(f"  - {dns}")
    print(f"\nValid for: {info['valid_days']} days")
    print(f"\nSHA-256 Fingerprint:")
    print(f"  {info['fingerprint']}")
    print("\nFiles created:")
    print(f"  - {key_path} (KEEP SECRET)")
    print(f"  - {cert_path} (distribute to clients)")


def verify_cert_validity(cert_path):
    with open(cert_path, "r") as f:
        data = f.read()
    cert = x509.load_pem_x509_certificate(data)
    
    if datetime.utcnow() > cert.not_valid_after_utc:
        return False
    
    return True