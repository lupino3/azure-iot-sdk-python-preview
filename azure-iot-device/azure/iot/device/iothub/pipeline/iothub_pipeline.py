# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_stages_mqtt,
)
from . import (
    constant,
    pipeline_stages_iothub,
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_stages_iothub_mqtt,
)
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider

logger = logging.getLogger(__name__)


class IoTHubPipeline(object):
    def __init__(self, auth_provider):
        """
        Constructor for instantiating a pipeline adapter object
        :param auth_provider: The authentication provider
        """
        self.feature_enabled = {
            constant.C2D_MSG: False,
            constant.INPUT_MSG: False,
            constant.METHODS: False,
            constant.TWIN: False,
            constant.TWIN_PATCHES: False,
        }

        # Event Handlers - Will be set by Client after instantiation of this object
        self.on_connected = None
        self.on_disconnected = None
        self.on_c2d_message_received = None
        self.on_input_message_received = None
        self.on_method_request_received = None
        self.on_twin_patch_received = None

        self._pipeline = (
            pipeline_stages_base.PipelineRootStage()
            .append_stage(pipeline_stages_iothub.UseAuthProviderStage())
            .append_stage(pipeline_stages_iothub.HandleTwinOperationsStage())
            .append_stage(pipeline_stages_base.CoordinateRequestAndResponseStage())
            .append_stage(pipeline_stages_iothub_mqtt.IoTHubMQTTConverterStage())
            .append_stage(pipeline_stages_base.EnsureConnectionStage())
            .append_stage(pipeline_stages_base.SerializeConnectOpsStage())
            .append_stage(pipeline_stages_mqtt.MQTTTransportStage())
        )

        def _on_pipeline_event(event):
            if isinstance(event, pipeline_events_iothub.C2DMessageEvent):
                if self.on_c2d_message_received:
                    self.on_c2d_message_received(event.message)
                else:
                    logger.warning("C2D message event received with no handler.  dropping.")

            elif isinstance(event, pipeline_events_iothub.InputMessageEvent):
                if self.on_input_message_received:
                    self.on_input_message_received(event.input_name, event.message)
                else:
                    logger.warning("input message event received with no handler.  dropping.")

            elif isinstance(event, pipeline_events_iothub.MethodRequestEvent):
                if self.on_method_request_received:
                    self.on_method_request_received(event.method_request)
                else:
                    logger.warning("Method request event received with no handler. Dropping.")

            elif isinstance(event, pipeline_events_iothub.TwinDesiredPropertiesPatchEvent):
                if self.on_twin_patch_received:
                    self.on_twin_patch_received(event.patch)
                else:
                    logger.warning("Twin patch event received with no handler. Dropping.")

            else:
                logger.warning("Dropping unknown pipeline event {}".format(event.name))

        def _on_connected():
            if self.on_connected:
                self.on_connected()

        def _on_disconnected():
            if self.on_disconnected:
                self.on_disconnected()

        self._pipeline.on_pipeline_event_handler = _on_pipeline_event
        self._pipeline.on_connected_handler = _on_connected
        self._pipeline.on_disconnected_handler = _on_disconnected

        def remove_this_code(call):
            if call.error:
                raise call.error

        if isinstance(auth_provider, X509AuthenticationProvider):
            op = pipeline_ops_iothub.SetX509AuthProviderOperation(
                auth_provider=auth_provider, callback=remove_this_code
            )
        else:  # Currently everything else goes via this block.
            op = pipeline_ops_iothub.SetAuthProviderOperation(
                auth_provider=auth_provider, callback=remove_this_code
            )

        self._pipeline.run_op(op)

    def connect(self, callback=None):
        """
        Connect to the service.

        :param callback: callback which is called when the connection to the service is complete.
        """
        logger.info("Starting ConnectOperation on the pipeline")

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)  # TODO: raise an error instead
            if callback:
                callback()

        self._pipeline.run_op(pipeline_ops_base.ConnectOperation(callback=on_complete))

    def disconnect(self, callback=None):
        """
        Disconnect from the service.

        :param callback: callback which is called when the connection to the service has been disconnected
        """
        logger.info("Starting DisconnectOperation on the pipeline")

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(pipeline_ops_base.DisconnectOperation(callback=on_complete))

    def send_d2c_message(self, message, callback=None):
        """
        Send a telemetry message to the service.

        :param message: message to send.
        :param callback: callback which is called when the message publish has been acknowledged by the service.
        """

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_iothub.SendD2CMessageOperation(message=message, callback=on_complete)
        )

    def send_output_event(self, message, callback=None):
        """
        Send an output message to the service.

        :param message: message to send.
        :param callback: callback which is called when the message publish has been acknowledged by the service.
        """

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_iothub.SendOutputEventOperation(message=message, callback=on_complete)
        )

    def send_method_response(self, method_response, callback=None):
        """
        Send a method response to the service.

        :param method_response: the method response to send
        :param callback: callback which is called when response has been acknowledged by the service
        """
        logger.info("IoTHubPipeline send_method_response called")

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_iothub.SendMethodResponseOperation(
                method_response=method_response, callback=on_complete
            )
        )

    def get_twin(self, callback):
        """
        Send a request for a full twin to the service.

        :param callback: callback which is called when request has been acknowledged by the service.
        This callback should have one parameter, which will contain the requested twin when called.
        """

        def on_complete(call):
            if call.error:
                sys.exit(1)
            if callback:
                callback(call.twin)

        self._pipeline.run_op(pipeline_ops_iothub.GetTwinOperation(callback=on_complete))

    def patch_twin_reported_properties(self, patch, callback=None):
        """
        Send a patch for a twin's reported properties to the service.

        :param patch: the reported properties patch to send
        :param callback: callback which is called when request has been acknowledged by the service.
        """

        def on_complete(call):
            if call.error:
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
                patch=patch, callback=on_complete
            )
        )

    def enable_feature(self, feature_name, callback=None):
        """
        Enable the given feature by subscribing to the appropriate topics.

        :param feature_name: one of the feature name constants from constant.py
        :param callback: callback which is called when the feature is enabled

        :raises: ValueError if feature_name is invalid
        """
        logger.info("enable_feature {} called".format(feature_name))
        if feature_name not in self.feature_enabled:
            raise ValueError("Invalid feature_name")
        self.feature_enabled[feature_name] = True

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_base.EnableFeatureOperation(
                feature_name=feature_name, callback=on_complete
            )
        )

    def disable_feature(self, feature_name, callback=None):
        """
        Disable the given feature by subscribing to the appropriate topics.
        :param callback: callback which is called when the feature is disabled

        :param feature_name: one of the feature name constants from constant.py

        :raises: ValueError if feature_name is invalid
        """
        logger.info("disable_feature {} called".format(feature_name))
        if feature_name not in self.feature_enabled:
            raise ValueError("Invalid feature_name")
        self.feature_enabled[feature_name] = False

        def on_complete(call):
            if call.error:
                # TODO we need error semantics on the client
                sys.exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_base.DisableFeatureOperation(
                feature_name=feature_name, callback=on_complete
            )
        )
