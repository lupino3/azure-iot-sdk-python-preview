import os


def is_root_key_there():
    if os.path.exists("ca_key.pem"):
        print("root key present")
    else:
        print("intermediate key absent")


def is_root_cert_there():
    if os.path.exists("ca_cert.pem"):
        print("root cert present")
    else:
        print("root cert absent")


def is_intermediate_key_there():
    if os.path.exists("demoCA/private/intermediate_key.pem"):
        print("intermediate key present")
    else:
        print("intermediate key absent")


def is_intermediate_csr_there():
    if os.path.exists("demoCA/newcerts/intermediate_csr.pem"):
        print("intermediate CSR present")
    else:
        print("intermediate CSR absent")


def is_intermediate_cert_there():
    if os.path.exists("demoCA/newcerts/intermediate_cert.pem"):
        print("intermediate cert present")
    else:
        print("intermediate cert absent")


if __name__ == '__main__':
    is_root_key_there()
    is_root_cert_there()
    is_intermediate_key_there()
    is_intermediate_csr_there()
    is_intermediate_cert_there()

