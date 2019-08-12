# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.common.connection_string import ConnectionString

logging.basicConfig(level=logging.INFO)


"""
tests for failures in pipeline constructors
tests for failures in all pipeline ops, sync and async
tests for new async_adapter
tests for evented_callback
look at windiff to see what other tests need to be added
ZZZ
"""
