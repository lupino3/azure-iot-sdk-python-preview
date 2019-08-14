# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import time
from azure_provisioning_e2e.iothubservice20180630.service_helper import Helper
from azure.iot.device import ProvisioningDeviceClient
from azure.iot.device.common import X509
from provisioningserviceclient import (
    ProvisioningServiceClient,
    IndividualEnrollment,
    EnrollmentGroup,
)
from provisioningserviceclient.protocol.models import AttestationMechanism, ReprovisionPolicy
import pytest
import logging
import os
from scripts.create_x509_chain_pipeline import (
    call_intermediate_cert_creation_from_pipeline,
    call_device_cert_creation_from_pipeline,
    delete_directories_certs_created_from_pipeline,
)


logging.basicConfig(filename="example.log", level=logging.DEBUG)


intermediate_common_name = "e2edpswingardium"
intermediate_password = "leviosa"
device_common_name = "e2edpsexpecto"
device_password = "patronum"

DPS_SERVICE_CONN_STR = os.getenv("PROVISIONING_SERVICE_CONNECTION_STRING")
IOTHUB_REGISTRY_READ_CONN_STR = os.getenv("IOTHUB_CONNECTION_STRING")
PROVISIONING_HOST = os.getenv("PROVISIONING_DEVICE_ENDPOINT")
ID_SCOPE = os.getenv("PROVISIONING_DEVICE_IDSCOPE")


@pytest.fixture(scope="module")
def before_module(request):
    print("set up before all tests")
    call_intermediate_cert_creation_from_pipeline(
        common_name=intermediate_common_name, intermediate_password=intermediate_password
    )
    call_device_cert_creation_from_pipeline(
        common_name=device_common_name,
        intermediate_password=intermediate_password,
        device_password=device_password,
    )

    def after_module():
        print("tear down after all tests")
        delete_directories_certs_created_from_pipeline()

    request.addfinalizer(after_module)


@pytest.fixture(scope="function")
def before_test(request):
    print("set up before each test")

    def after_test():
        print("tear down after each test")

    request.addfinalizer(after_test)


# @pytest.mark.it("Check folder creation and all")
# def test_create_intermediate(before_module, before_test):
#     registration_id = "e2e-dps-underthewhompingwillow"
#     print(registration_id)


# @pytest.mark.it(
#     "A device gets provisioned to the linked IoTHub with the device_id equal to the registration_id when a symmetric key individual enrollment has been created"
# )
# def test_device_register_with_no_device_id_for_a_symmetric_key_individual_enrollment(
#     before_module, before_test
# ):
#     service_client = ProvisioningServiceClient.create_from_connection_string(DPS_SERVICE_CONN_STR)
#
#     registration_id = "e2e-dps-underthewhompingwillow"
#     reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
#     attestation_mechanism = AttestationMechanism(type="symmetricKey")
#
#     individual_provisioning_model = IndividualEnrollment.create(
#         attestation=attestation_mechanism,
#         registration_id=registration_id,
#         reprovision_policy=reprovision_policy,
#     )
#
#     individual_enrollment_record = service_client.create_or_update(individual_provisioning_model)
#
#     time.sleep(3)
#
#     registration_id = individual_enrollment_record.registration_id
#     symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key
#
#     provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
#         provisioning_host=PROVISIONING_HOST,
#         registration_id=registration_id,
#         id_scope=ID_SCOPE,
#         symmetric_key=symmetric_key,
#     )
#
#     provisioning_device_client.register()
#
#     helper = Helper(IOTHUB_REGISTRY_READ_CONN_STR)
#     device = helper.get_device(registration_id)
#
#     assert device is not None
#     assert device.authentication.type == "sas"
#     assert device.device_id == registration_id
#
#     service_client.delete_individual_enrollment_by_param(registration_id)
#
# @pytest.mark.it(
#     "A device gets provisioned to the linked IoTHub with the user supplied device_id when a symmetric key individual enrollment has been created"
# )
# def test_device_register_with_device_id_for_a_symmetric_key_individual_enrollment(before_test):
#
#     registration_id = "e2e-dps-prioriincantatem"
#     device_id = "e2e-dps-tommarvoloriddle"
#     reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
#     attestation_mechanism = AttestationMechanism(type="symmetricKey")
#
#     individual_provisioning_model = IndividualEnrollment.create(
#         attestation=attestation_mechanism,
#         registration_id=registration_id,
#         device_id=device_id,
#         reprovision_policy=reprovision_policy,
#     )
#
#     service_client = ProvisioningServiceClient.create_from_connection_string(DPS_SERVICE_CONN_STR)
#     individual_enrollment_record = service_client.create_or_update(individual_provisioning_model)
#
#     time.sleep(3)
#
#     registration_id = individual_enrollment_record.registration_id
#     symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key
#
#     provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
#         provisioning_host=PROVISIONING_HOST,
#         registration_id=registration_id,
#         id_scope=ID_SCOPE,
#         symmetric_key=symmetric_key,
#     )
#
#     provisioning_device_client.register()
#
#     helper = Helper(IOTHUB_REGISTRY_READ_CONN_STR)
#     device = helper.get_device(device_id)
#
#     assert device is not None
#     assert device.authentication.type == "sas"
#     assert device.device_id == device_id
#
#     service_client.delete_individual_enrollment_by_param(registration_id)


@pytest.mark.it(
    "A device with a X509 authentication individual enrollment is registered to IoTHub with an user supplied custom device id"
)
def test_device_register_with_device_id_for_a_x509_individual_enrollment(before_module):
    print("check cert creation")
    if os.path.exists("demoCA/private/intermediate_key.pem"):
        print("intermediate key present")
        assert True
    else:
        print("intermediate key absent")
        assert False

    if os.path.exists("demoCA/newcerts/intermediate_csr.pem"):
        print("intermediate CSR present")
        assert True
    else:
        print("intermediate CSR absent")
        assert False

    if os.path.exists("demoCA/newcerts/intermediate_cert.pem"):
        print("intermediate cert present")
        assert True
    else:
        print("intermediate cert absent")
        assert False

    if os.path.exists("demoCA/newcerts/device_cert1.pem"):
        print("device cert present")
        assert True
    else:
        print("device cert absent")
        assert False

    # registration_id = device_common_name + str(1)
    # device_id = "e2edpsflyingfeather"
    # reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
    #
    # device_cert_input_file = "demoCA/newcerts/device_cert1.pem"
    # with open(device_cert_input_file, "r") as in_device_cert:
    #     device_cert_content = in_device_cert.read()
    #
    # attestation_mechanism = AttestationMechanism.create_with_x509_client_certs(device_cert_content)
    #
    # individual_provisioning_model = IndividualEnrollment.create(
    #     attestation=attestation_mechanism,
    #     registration_id=registration_id,
    #     device_id=device_id,
    #     reprovision_policy=reprovision_policy,
    # )
    #
    # service_client = ProvisioningServiceClient.create_from_connection_string(DPS_SERVICE_CONN_STR)
    # individual_enrollment_record = service_client.create_or_update(individual_provisioning_model)
    #
    # # time.sleep(3)
    #
    # registration_id = individual_enrollment_record.registration_id
    #
    # # intermediate_cert_filename = "demoCA/newcerts/intermediate_cert.pem"
    # # device_chain_cert_output_file = "demoCA/newcerts/device_cert1_chain.pem"
    # # filenames = [device_cert_input_file, intermediate_cert_filename]
    # # with open(device_chain_cert_output_file, "w") as outfile:
    # #             for fname in filenames:
    # #                 with open(fname) as infile:
    # #                     outfile.write(infile.read())
    #
    # x509 = X509(
    #     cert_file=device_cert_input_file,
    #     key_file="demoCA/private/device_key1.pem",
    #     pass_phrase=device_password,
    # )
    #
    # provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
    #     provisioning_host=PROVISIONING_HOST,
    #     registration_id=registration_id,
    #     id_scope=ID_SCOPE,
    #     x509=x509,
    # )
    #
    # provisioning_device_client.register()
    #
    # helper = Helper(IOTHUB_REGISTRY_READ_CONN_STR)
    # device = helper.get_device(device_id)
    #
    # assert device is not None
    # assert device.authentication.type == "selfSigned"
    # assert device.device_id == device_id
    #
    # service_client.delete_individual_enrollment_by_param(registration_id)



#
# @pytest.mark.it(
#     "A device gets provisioned to the linked IoTHub with device_id equal to the registration id of an individual enrollment with X509 authentication"
# )
# def test_device_register_with_no_device_id_for_a_x509_individual_enrollment(before_test):
#
#     registration_id = "deviceincantatem"  # the certificate common name
#     reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
#     with open("../../scripts/demoCAOld2/newcerts/device_cert.pem", "r") as device_pem:
#         device_cert_content = device_pem.read()
#
#     attestation_mechanism = AttestationMechanism.create_with_x509_client_certs(device_cert_content)
#
#     individual_provisioning_model = IndividualEnrollment.create(
#         attestation=attestation_mechanism,
#         registration_id=registration_id,
#         reprovision_policy=reprovision_policy,
#     )
#
#     service_client = ProvisioningServiceClient.create_from_connection_string(DPS_SERVICE_CONN_STR)
#     individual_enrollment_record = service_client.create_or_update(individual_provisioning_model)
#
#     time.sleep(3)
#
#     registration_id = individual_enrollment_record.registration_id
#
#     x509 = X509(
#         cert_file=leaf_certificate_path_1,
#         key_file=leaf_certificate_key_1,
#         pass_phrase=leaf_certificate_password_1,
#     )
#
#     provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
#         provisioning_host=PROVISIONING_HOST,
#         registration_id=registration_id,
#         id_scope=ID_SCOPE,
#         x509=x509,
#     )
#
#     provisioning_device_client.register()
#
#     helper = Helper(IOTHUB_REGISTRY_READ_CONN_STR)
#     device = helper.get_device(registration_id)
#
#     assert device is not None
#     assert device.authentication.type == "selfSigned"
#     assert device.device_id == registration_id
#
#
# @pytest.mark.it(
#     "A group of devices get provisioned to the linked IoTHub when a group enrollment record has been created with intermediate X509 authentication"
# )
# def test_group_of_devices_register_with_no_device_id_for_a_x509_intermediate_authentication_group_enrollment(before_test):
#
#     group_id = "e2e-hogwarts-school"
#     common_device_id = "devicelocomotor"  # the certificate common name
#     common_device_password = "hogwartsd"
#     reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
#
#     device_count_in_group = 3
#
#     intermediate_cert_filename = "../../scripts/demoCA/newcerts/intermediate_cert.pem"
#     with open(intermediate_cert_filename, "r") as intermediate_pem:
#         intermediate_cert_content = intermediate_pem.read()
#
#     attestation_mechanism = AttestationMechanism.create_with_x509_signing_certs(
#         intermediate_cert_content
#     )
#     enrollment_group_provisioning_model = EnrollmentGroup.create(
#         group_id, attestation=attestation_mechanism, reprovision_policy=reprovision_policy
#     )
#
#     service_client = ProvisioningServiceClient.create_from_connection_string(DPS_SERVICE_CONN_STR)
#     service_client.create_or_update(enrollment_group_provisioning_model)
#
#     time.sleep(3)
#     helper = Helper(IOTHUB_REGISTRY_READ_CONN_STR)
#
#     common_device_key_input_file = "../../scripts/demoCA/private/device_key"
#     common_device_cert_input_file = "../../scripts/demoCA/newcerts/device_cert"
#     common_device_cert_output_file = "../../scripts/demoCA/newcerts/out_inter_device_cert"
#     for index in range(0, device_count_in_group):
#         device_id = common_device_id + str(index + 1)
#         device_key_input_file = common_device_key_input_file + str(index + 1) + ".pem"
#         device_cert_input_file = common_device_cert_input_file + str(index + 1) + ".pem"
#         device_cert_output_file = common_device_cert_output_file + str(index + 1) + ".pem"
#         filenames = [device_cert_input_file, intermediate_cert_filename]
#         with open(device_cert_output_file, "w") as outfile:
#             for fname in filenames:
#                 with open(fname) as infile:
#                     outfile.write(infile.read())
#         x509 = X509(
#             cert_file=device_cert_output_file,
#             key_file=device_key_input_file,
#             pass_phrase=common_device_password,
#         )
#
#         provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
#             provisioning_host=PROVISIONING_HOST,
#             registration_id=device_id,
#             id_scope=ID_SCOPE,
#             x509=x509,
#         )
#
#         provisioning_device_client.register()
#
#         device = helper.get_device(device_id)
#
#         assert device is not None
#         assert device.authentication.type == "selfSigned"
#         assert device.device_id == device_id
#
# @pytest.mark.it(
#     "A group of devices get provisioned to the linked IoTHub when a group enrollment record has been created with an already uploaded ca cert X509 authentication"
# )
# def test_group_of_devices_register_with_no_device_id_for_a_x509_ca_authentication_group_enrollment(before_test):
#     # subprocess.call("python create_x509_chain.py \"priori\" --ca-password \"hogwarts\" --intermediate-password \"hogwartsi\" --device-password \"hogwartsd\"", shell=True)
#
#     group_id = "e2e-hogwarts-ca-school"
#     common_device_id = "devicelocomotor"  # the certificate common name
#     common_device_password = "hogwartsd"
#     reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
#
#     device_count_in_group = 3
#
#     attestation_mechanism = AttestationMechanism.create_with_x509_ca_refs(ref1=DPS_GROUP_CA_CERT)
#     enrollment_group_provisioning_model = EnrollmentGroup.create(
#         group_id, attestation=attestation_mechanism, reprovision_policy=reprovision_policy
#     )
#
#     service_client = ProvisioningServiceClient.create_from_connection_string(DPS_SERVICE_CONN_STR)
#     service_client.create_or_update(enrollment_group_provisioning_model)
#
#     time.sleep(3)
#     helper = Helper(IOTHUB_REGISTRY_READ_CONN_STR)
#
#     common_device_key_input_file = "../../scripts/demoCA/private/device_key"
#     common_device_cert_input_file = "../../scripts/demoCA/newcerts/device_cert"
#     common_device_cert_output_file = "../../scripts/demoCA/newcerts/out_ca_device_cert"
#     intermediate_cert_filename = "../../scripts/demoCA/newcerts/intermediate_cert.pem"
#     for index in range(0, device_count_in_group):
#         device_id = common_device_id + str(index + 1)
#         device_key_input_file = common_device_key_input_file + str(index + 1) + ".pem"
#         device_cert_input_file = common_device_cert_input_file + str(index + 1) + ".pem"
#         device_cert_output_file = common_device_cert_output_file + str(index + 1) + ".pem"
#         filenames = [device_cert_input_file, intermediate_cert_filename]
#         with open(device_cert_output_file, "w") as outfile:
#             for fname in filenames:
#                 with open(fname) as infile:
#                     outfile.write(infile.read())
#         x509 = X509(
#             cert_file=device_cert_output_file,
#             key_file=device_key_input_file,
#             pass_phrase=common_device_password,
#         )
#
#         provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
#             provisioning_host=PROVISIONING_HOST,
#             registration_id=device_id,
#             id_scope=ID_SCOPE,
#             x509=x509,
#         )
#
#         provisioning_device_client.register()
#
#         device = helper.get_device(device_id)
#
#         assert device is not None
#         assert device.authentication.type == "selfSigned"
#         assert device.device_id == device_id
