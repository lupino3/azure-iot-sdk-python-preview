# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import six
from azure.iot.device.common import errors, unhandled_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    pipeline_stages_mqtt,
)
from tests.common.pipeline.helpers import (
    assert_callback_failed,
    assert_callback_succeeded,
    all_common_ops,
    all_common_events,
    all_except,
    UnhandledException,
)
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


this_module = sys.modules[__name__]

fake_client_id = "__fake_client_id__"
fake_hostname = "__fake_hostname__"
fake_username = "__fake_username__"
fake_ca_cert = "__fake_ca_cert__"
fake_sas_token = "__fake_sas_token__"
fake_topic = "__fake_topic__"
fake_payload = "__fake_payload__"
fake_certificate = "__fake_certificate__"

ops_handled_by_this_stage = [
    pipeline_ops_base.ConnectOperation,
    pipeline_ops_base.DisconnectOperation,
    pipeline_ops_base.ReconnectOperation,
    pipeline_ops_mqtt.SetMQTTConnectionArgsOperation,
    pipeline_ops_mqtt.MQTTPublishOperation,
    pipeline_ops_mqtt.MQTTSubscribeOperation,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation,
]

events_handled_by_this_stage = []

# TODO: Potentially refactor this out to package level class that can be inherited
pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_mqtt.MQTTTransportStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=ops_handled_by_this_stage,
    all_events=all_common_events,
    handled_events=events_handled_by_this_stage,
    methods_that_enter_pipeline_thread=[
        "_on_mqtt_message_received",
        "_on_mqtt_connected",
        "_on_mqtt_connection_failure",
        "_on_mqtt_disconnected",
    ],
)


@pytest.fixture
def stage(mocker):
    stage = pipeline_stages_mqtt.MQTTTransportStage()
    root = pipeline_stages_base.PipelineRootStage()

    stage.previous = root
    root.next = stage
    stage.pipeline_root = root

    mocker.spy(root, "handle_pipeline_event")
    mocker.spy(root, "on_connected")
    mocker.spy(root, "on_disconnected")

    mocker.spy(stage, "_on_mqtt_connected")
    mocker.spy(stage, "_on_mqtt_connection_failure")
    mocker.spy(stage, "_on_mqtt_disconnected")

    return stage


@pytest.fixture
def transport(mocker):
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )
    return pipeline_stages_mqtt.MQTTTransport


@pytest.fixture
def op_set_connection_args(mocker):
    return pipeline_ops_mqtt.SetMQTTConnectionArgsOperation(
        client_id=fake_client_id,
        hostname=fake_hostname,
        username=fake_username,
        ca_cert=fake_ca_cert,
        client_cert=fake_certificate,
        sas_token=fake_sas_token,
        callback=mocker.MagicMock(),
    )


@pytest.fixture
def op_connect(mocker):
    return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())


@pytest.fixture
def op_reconnect(mocker):
    return pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())


@pytest.fixture
def op_disconnect(mocker):
    return pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())


@pytest.fixture
def op_publish(mocker):
    return pipeline_ops_mqtt.MQTTPublishOperation(
        topic=fake_topic, payload=fake_payload, callback=mocker.MagicMock()
    )


@pytest.fixture
def op_subscribe(mocker):
    return pipeline_ops_mqtt.MQTTSubscribeOperation(topic=fake_topic, callback=mocker.MagicMock())


@pytest.fixture
def op_unsubscribe(mocker):
    return pipeline_ops_mqtt.MQTTUnsubscribeOperation(topic=fake_topic, callback=mocker.MagicMock())


@pytest.fixture
def create_transport(stage, transport, op_set_connection_args):
    stage.run_op(op_set_connection_args)


# TODO: This should be a package level class inherited by all .run_op() tests in all stages
class RunOpTests(object):
    @pytest.mark.it(
        "Completes the operation with failure if an unexpected Exception is raised while executing the operation"
    )
    def test_completes_operation_with_error(self, mocker, stage):
        execution_exception = Exception()
        mock_op = mocker.MagicMock()
        stage._execute_op = mocker.MagicMock(side_effect=execution_exception)

        stage.run_op(mock_op)
        assert mock_op.error is execution_exception

    @pytest.mark.it(
        "Allows any BaseException that was raised during execution of the operation to propogate"
    )
    def test_base_exception_propogates(self, mocker, stage):
        execution_exception = BaseException()
        mock_op = mocker.MagicMock()
        stage._execute_op = mocker.MagicMock(side_effect=execution_exception)

        with pytest.raises(BaseException):
            stage.run_op(mock_op)


@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- called with pipeline_ops_mqtt.SetMQTTConnectionArgsOperation"
)
class TestMQTTProviderRunOpWithSetConnectionArgs(RunOpTests):
    @pytest.mark.it("Creates an MQTTTransport object")
    def test_creates_transport(self, stage, transport, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert transport.call_count == 1

    @pytest.mark.it(
        "Initializes the MQTTTransport object with the passed client_id, hostname, username, ca_cert and x509_cert"
    )
    def test_passes_right_params(self, stage, transport, mocker, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert transport.call_args == mocker.call(
            client_id=fake_client_id,
            hostname=fake_hostname,
            username=fake_username,
            ca_cert=fake_ca_cert,
            x509_cert=fake_certificate,
        )

    @pytest.mark.it("Sets handlers on the transport")
    def test_sets_parameters(self, stage, transport, mocker, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert transport.return_value.on_mqtt_disconnected_handler == stage._on_mqtt_disconnected
        assert transport.return_value.on_mqtt_connected_handler == stage._on_mqtt_connected
        assert (
            transport.return_value.on_mqtt_connection_failure_handler
            == stage._on_mqtt_connection_failure
        )
        assert (
            transport.return_value.on_mqtt_message_received_handler
            == stage._on_mqtt_message_received
        )

    @pytest.mark.it("Sets the pending connection op tracker to None")
    def test_pending_conn_op(self, stage, transport, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert stage._pending_connection_op is None

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_succeeds(self, stage, transport, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert_callback_succeeded(op=op_set_connection_args)


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with ConnectOperation")
class TestMQTTProviderExecuteOpWithConnect(RunOpTests):
    @pytest.mark.it("Sets the ConnectOperation as the pending connection operation")
    def test_sets_pending_operation(self, stage, create_transport, op_connect):
        stage.run_op(op_connect)
        assert stage._pending_connection_op is op_connect

    @pytest.mark.it("Cancels any already pending connection operation")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_pending_operation_cancelled(
        self, mocker, stage, create_transport, op_connect, pending_connection_op
    ):
        pending_connection_op.callback = mocker.MagicMock()
        stage._pending_connection_op = pending_connection_op
        stage.run_op(op_connect)

        # Callback has been completed, with a PipelineError set indicating early cancellation
        assert_callback_failed(op=pending_connection_op, error=errors.PipelineError)

        # New operation is now the pending operation
        assert stage._pending_connection_op is op_connect

    @pytest.mark.it("Does an MQTT connect via the MQTTTransport")
    def test_mqtt_connect(self, mocker, stage, create_transport, op_connect):
        stage.run_op(op_connect)
        assert stage.transport.connect.call_count == 1
        assert stage.transport.connect.call_args == mocker.call(password=stage.sas_token)

    @pytest.mark.it(
        "Fails the operation and resets the pending connection operation to None, if there is a failure connecting in the MQTTTransport"
    )
    def test_fails_operation(self, stage, create_transport, op_connect, fake_exception):
        stage.transport.connect.side_effect = fake_exception
        stage.run_op(op_connect)
        assert_callback_failed(op=op_connect, error=fake_exception)
        assert stage._pending_connection_op is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with ReconnectOperation")
class TestMQTTProviderExecuteOpWithReconnect(RunOpTests):
    @pytest.mark.it("Sets the ReconnectOperation as the pending connection operation")
    def test_sets_pending_operation(self, stage, create_transport, op_reconnect):
        stage.run_op(op_reconnect)
        assert stage._pending_connection_op is op_reconnect

    @pytest.mark.it("Cancels any already pending connection operation")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_pending_operation_cancelled(
        self, mocker, stage, create_transport, op_reconnect, pending_connection_op
    ):
        pending_connection_op.callback = mocker.MagicMock()
        stage._pending_connection_op = pending_connection_op
        stage.run_op(op_reconnect)

        # Callback has been completed, with a PipelineError set indicating early cancellation
        assert_callback_failed(op=pending_connection_op, error=errors.PipelineError)

        # New operation is now the pending operation
        assert stage._pending_connection_op is op_reconnect

    @pytest.mark.it("Does an MQTT reconnect via the MQTTTransport")
    def test_mqtt_reconnect(self, mocker, stage, create_transport, op_reconnect):
        stage.run_op(op_reconnect)
        assert stage.transport.reconnect.call_count == 1
        assert stage.transport.reconnect.call_args == mocker.call(password=stage.sas_token)

    @pytest.mark.it(
        "Fails the operation and resets the pending connection operation to None, if there is a failure reconnecting in the MQTTTransport"
    )
    def test_fails_operation(self, mocker, stage, create_transport, op_reconnect, fake_exception):
        stage.transport.reconnect.side_effect = fake_exception
        stage.run_op(op_reconnect)
        assert_callback_failed(op=op_reconnect, error=fake_exception)
        assert stage._pending_connection_op is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with DisconnectOperation")
class TestMQTTProviderExecuteOpWithDisconnect(RunOpTests):
    @pytest.mark.it("Sets the DisconnectOperation as the pending connection operation")
    def test_sets_pending_operation(self, stage, create_transport, op_disconnect):
        stage.run_op(op_disconnect)
        assert stage._pending_connection_op is op_disconnect

    @pytest.mark.it("Cancels any already pending connection operation")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_pending_operation_cancelled(
        self, mocker, stage, create_transport, op_disconnect, pending_connection_op
    ):
        pending_connection_op.callback = mocker.MagicMock()
        stage._pending_connection_op = pending_connection_op
        stage.run_op(op_disconnect)

        # Callback has been completed, with a PipelineError set indicating early cancellation
        assert_callback_failed(op=pending_connection_op, error=errors.PipelineError)

        # New operation is now the pending operation
        assert stage._pending_connection_op is op_disconnect

    @pytest.mark.it("Does an MQTT disconnect via the MQTTTransport")
    def test_mqtt_disconnect(self, mocker, stage, create_transport, op_disconnect):
        stage.run_op(op_disconnect)
        assert stage.transport.disconnect.call_count == 1
        assert stage.transport.disconnect.call_args == mocker.call()

    @pytest.mark.it(
        "Fails the operation and resets the pending connection operation to None, if there is a failure disconnecting in the MQTTTransport"
    )
    def test_fails_operation(self, mocker, stage, create_transport, op_disconnect, fake_exception):
        stage.transport.disconnect.side_effect = fake_exception
        stage.run_op(op_disconnect)
        assert_callback_failed(op=op_disconnect, error=fake_exception)
        assert stage._pending_connection_op is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with MQTTPublishOperation")
class TestMQTTProviderExecuteOpWithMQTTPublishOperation(RunOpTests):
    @pytest.mark.it("Does an MQTT publish via the MQTTTransport")
    def test_mqtt_publish(self, mocker, stage, create_transport, op_publish):
        stage.run_op(op_publish)
        assert stage.transport.publish.call_count == 1
        assert stage.transport.publish.call_args == mocker.call(
            topic=op_publish.topic, payload=op_publish.payload, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Completes the operation with success, upon successful completion of the MQTT publish"
    )
    def test_complete(self, mocker, stage, create_transport, op_publish):
        # Begin publish
        stage.run_op(op_publish)

        # Trigger publish completion
        stage.transport.publish.call_args[1]["callback"]()

        assert_callback_succeeded(op=op_publish)


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with MQTTSubscribeOperation")
class TestMQTTProviderExecuteOpWithMQTTSubscribeOperation(RunOpTests):
    @pytest.mark.it("Does an MQTT subscribe via the MQTTTransport")
    def test_mqtt_publish(self, mocker, stage, create_transport, op_subscribe):
        stage.run_op(op_subscribe)
        assert stage.transport.subscribe.call_count == 1
        assert stage.transport.subscribe.call_args == mocker.call(
            topic=op_subscribe.topic, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Completes the operation with success, upon successful completion of the MQTT subscribe"
    )
    def test_complete(self, mocker, stage, create_transport, op_subscribe):
        # Begin subscribe
        stage.run_op(op_subscribe)

        # Trigger subscribe completion
        stage.transport.subscribe.call_args[1]["callback"]()

        assert_callback_succeeded(op=op_subscribe)


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with MQTTUnsubscribeOperation")
class TestMQTTProviderExecuteOpWithMQTTUnsubscribeOperation(RunOpTests):
    @pytest.mark.it("Does an MQTT unsubscribe via the MQTTTransport")
    def test_mqtt_publish(self, mocker, stage, create_transport, op_unsubscribe):
        stage.run_op(op_unsubscribe)
        assert stage.transport.unsubscribe.call_count == 1
        assert stage.transport.unsubscribe.call_args == mocker.call(
            topic=op_unsubscribe.topic, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Completes the operation with success, upon successful completion of the MQTT unsubscribe"
    )
    def test_complete(self, mocker, stage, create_transport, op_unsubscribe):
        # Begin unsubscribe
        stage.run_op(op_unsubscribe)

        # Trigger unsubscribe completion
        stage.transport.unsubscribe.call_args[1]["callback"]()

        assert_callback_succeeded(op=op_unsubscribe)


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT message received")
class TestMQTTProviderProtocolClientEvents(object):
    @pytest.mark.it("Fires an IncomingMQTTMessageEvent event for each MQTT message received")
    def test_incoming_message_handler(self, stage, create_transport, mocker):
        stage.transport.on_mqtt_message_received_handler(topic=fake_topic, payload=fake_payload)
        assert stage.previous.handle_pipeline_event.call_count == 1
        call_arg = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(call_arg, pipeline_events_mqtt.IncomingMQTTMessageEvent)

    @pytest.mark.it("Passes topic and payload as part of the IncomingMQTTMessageEvent event")
    def test_verify_incoming_message_attributes(self, stage, create_transport, mocker):
        stage.transport.on_mqtt_message_received_handler(topic=fake_topic, payload=fake_payload)
        call_arg = stage.previous.handle_pipeline_event.call_args[0][0]
        assert call_arg.payload == fake_payload
        assert call_arg.topic == fake_topic


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT connected")
class TestMQTTProviderOnConnected(object):
    @pytest.mark.it("Calls self.on_connected when the transport connected event fires")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_connected_handler(self, stage, create_transport, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        assert stage.previous.on_connected.call_count == 0
        stage.transport.on_mqtt_connected_handler()
        assert stage.previous.on_connected.call_count == 1

    @pytest.mark.it(
        "Completes a pending ConnectOperation with success when the transport connected event fires"
    )
    def test_completes_pending_connect_op(self, mocker, stage, create_transport):
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_connected_handler()
        assert_callback_succeeded(op=op)
        assert stage._pending_connection_op is None

    @pytest.mark.it(
        "Completes a pending ReconnectOperation with success when the transport connected event fires"
    )
    def test_completes_pending_reconnect_op(self, mocker, stage, create_transport):
        op = pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_connected_handler()
        assert_callback_succeeded(op=op)
        assert stage._pending_connection_op is None

    @pytest.mark.it(
        "Ignores a pending DisconnectOperation when the transport connected event fires"
    )
    def test_ignores_pending_disconnect_op(self, mocker, stage, create_transport):
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_connected_handler()
        # handler did NOT trigger a callback
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op


@pytest.mark.describe("MQTTTarnsportStage - EVENT: MQTT connection failure")
class TestMQTTProviderOnConnectionFailure(object):
    @pytest.mark.it(
        "Does not call self.on_connected when the transport connection failure event fires"
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_does_not_call_connected_handler(
        self, stage, create_transport, fake_exception, pending_connection_op
    ):
        # This test is testing negative space - something the function does NOT do - rather than something it does
        stage._pending_connection_op = pending_connection_op
        assert stage.previous.on_connected.call_count == 0
        stage.transport.on_mqtt_connection_failure_handler(fake_exception)
        assert stage.previous.on_connected.call_count == 0

    @pytest.mark.it("Fails a pending ConnectOperation if the connection failure event fires")
    def test_fails_pending_connect_op(self, mocker, stage, create_transport, fake_exception):
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_connection_failure_handler(fake_exception)
        assert_callback_failed(op=op, error=fake_exception)
        assert stage._pending_connection_op is None

    @pytest.mark.it("Fails a pending ReconnectOperation if the connection failure event fires")
    def test_fails_pending_reconnect_op(self, mocker, stage, create_transport, fake_exception):
        op = pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_connection_failure_handler(fake_exception)
        assert_callback_failed(op=op, error=fake_exception)
        assert stage._pending_connection_op is None

    @pytest.mark.it("Ignores a pending DisconnectOperation if the connection failure event fires")
    def test_ignores_pending_disconnect_op(self, mocker, stage, create_transport, fake_exception):
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_connection_failure_handler(fake_exception)
        # Assert nothing changed about the operation
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op

    @pytest.mark.it(
        "Triggers the unhandled exception handler (with error cause) when the connection failure is unexpected"
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_unexpected_connection_failure(
        self, mocker, stage, create_transport, fake_exception, pending_connection_op
    ):
        # A connection failure is unexpected if there is not a pending Connect/Reconnect operation
        # i.e. "Why did we get a connection failure? We weren't even trying to connect!"
        mock_handler = mocker.patch.object(
            unhandled_exceptions, "exception_caught_in_background_thread"
        )
        stage._pending_connection_operation = pending_connection_op
        stage.transport.on_mqtt_connection_failure_handler(fake_exception)
        assert mock_handler.call_count == 1
        assert mock_handler.call_args[0][0] is fake_exception


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT disconnected")
class TestMQTTProviderOnDisconnected(object):
    @pytest.mark.it("Calls self.on_disconnected when the transport disconnected event fires")
    @pytest.mark.parametrize(
        "cause",
        [pytest.param(None, id="No error cause"), pytest.param(Exception(), id="With error cause")],
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
            pytest.param(pipeline_ops_base.DisconnectOperation(), id="Pending DisconnectOperation"),
        ],
    )
    def test_disconnected_handler(self, stage, create_transport, pending_connection_op, cause):
        stage._pending_connection_op = pending_connection_op
        assert stage.previous.on_disconnected.call_count == 0
        stage.transport.on_mqtt_disconnected_handler(cause)
        assert stage.previous.on_disconnected.call_count == 1

    @pytest.mark.it(
        "Completes a pending DisconnectOperation with success when the transport disconnected event fires without an error cause"
    )
    def test_compltetes_pending_disconnect_op_when_no_error(self, mocker, stage, create_transport):
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_disconnected_handler(None)
        assert_callback_succeeded(op=op)
        assert stage._pending_connection_op is None

    @pytest.mark.it(
        "Completes a pending DisconnectOperation with failure (from ConnectionDroppedError) when the transport disconnected event fires with an error cause"
    )
    def test_completes_pending_disconnect_op_with_error(
        self, mocker, stage, create_transport, fake_exception
    ):
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert op.callback.call_count == 0
        assert stage._pending_connection_op is op
        stage.transport.on_mqtt_disconnected_handler(fake_exception)
        assert_callback_failed(op=op, error=errors.ConnectionDroppedError)
        assert stage._pending_connection_op is None
        if six.PY3:
            assert op.error.__cause__ is fake_exception

    @pytest.mark.it(
        "Ignores an unrelated pending operation when the transport disconnected event fires"
    )
    @pytest.mark.parametrize(
        "cause",
        [pytest.param(None, id="No error cause"), pytest.param(Exception(), id="With error cause")],
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
        ],
    )
    def test_ignores_unrelated_op(
        self, mocker, stage, create_transport, pending_connection_op, cause
    ):
        stage._pending_connection_op = pending_connection_op
        stage.transport.on_mqtt_disconnected_handler(cause)
        # The unrelated pending operation is STILL the pending connection op
        assert stage._pending_connection_op is pending_connection_op

    @pytest.mark.it(
        "Triggers the unhandled exception handler (with ConnectionDroppedError) when the disconnect is unexpected"
    )
    @pytest.mark.parametrize(
        "cause",
        [pytest.param(None, id="No error cause"), pytest.param(Exception(), id="With error cause")],
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.ConnectOperation(), id="Pending ConnectOperation"),
            pytest.param(pipeline_ops_base.ReconnectOperation(), id="Pending ReconnectOperation"),
        ],
    )
    def test_unexpected_disconnect(
        self, mocker, stage, create_transport, pending_connection_op, cause
    ):
        # A disconnect is unexpected when there is no pending operation, or a pending, non-Disconnect operation
        mock_handler = mocker.patch.object(
            unhandled_exceptions, "exception_caught_in_background_thread"
        )
        stage._pending_connection_op = pending_connection_op
        stage.transport.on_mqtt_disconnected_handler(cause)
        assert mock_handler.call_count == 1
        assert isinstance(mock_handler.call_args[0][0], errors.ConnectionDroppedError)
        if six.PY3:
            assert mock_handler.call_args[0][0].__cause__ is cause
