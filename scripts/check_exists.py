import os


def is_intermediate_key_there():
    if os.path.exists("demoCA/private/intermediate_key.pem"):
        print("intermediate key present")
    else:
        print("intermediate key absent")


def is_intermediate_cert_there():
    if os.path.exists("demoCA/newcerts/intermediate_cert.pem"):
        print("intermediate cert present")
    else:
        print("intermediate cert absent")


if __name__ == '__main__':
    is_intermediate_key_there()
    is_intermediate_cert_there()

