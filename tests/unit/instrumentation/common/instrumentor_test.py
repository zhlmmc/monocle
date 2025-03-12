import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import SpanContext
from opentelemetry.sdk.trace.export import SpanProcessor
from monocle_apptrace.instrumentation.common.instrumentor import (
    MonocleInstrumentor,
    setup_monocle_telemetry,
    start_trace,
    stop_trace,
    on_processor_start,
    start_scope,
    stop_scope,
    monocle_trace_scope,
    monocle_trace_scope_method,
    monocle_trace_http_route,
    FixedIdGenerator
)
from monocle_apptrace.instrumentation.common.span_handler import SpanHandler
from monocle_apptrace.instrumentation.common.wrapper_method import WrapperMethod

@pytest.fixture
def tracer_provider():
    return TracerProvider()

@pytest.fixture
def span_processor():
    return Mock(spec=SpanProcessor)

@pytest.fixture
def mock_span():
    span = Mock()
    span.set_attribute = Mock()
    span.end = Mock()
    return span

def test_get_instrumentor(tracer_provider):
    instrumentor = MonocleInstrumentor(handlers={})
    tracer = Mock()
    wrapped_func = instrumentor.get_instrumentor(tracer)
    assert callable(wrapped_func)

def test_instrumentation_dependencies():
    instrumentor = MonocleInstrumentor(handlers={})
    deps = instrumentor.instrumentation_dependencies()
    assert isinstance(deps, tuple)
    assert len(deps) == 0

@pytest.mark.asyncio
async def test_setup_monocle_telemetry():
    workflow_name = "test_workflow"
    span_processor = Mock(spec=SpanProcessor)

    with patch('monocle_apptrace.instrumentation.common.instrumentor.get_monocle_exporter') as mock_exporter:
        mock_exporter.return_value = []
        instrumentor = setup_monocle_telemetry(
            workflow_name=workflow_name,
            span_processors=[span_processor]
        )
        assert isinstance(instrumentor, MonocleInstrumentor)

def test_on_processor_start(mock_span):
    context_props = {"key": "value"}
    with patch('monocle_apptrace.instrumentation.common.instrumentor.get_value') as mock_get_value:
        mock_get_value.return_value = context_props
        on_processor_start(mock_span, None)
        mock_span.set_attribute.assert_called_with("session.key", "value")

def test_start_trace():
    mock_tracer = Mock()
    mock_span = Mock()
    mock_tracer.start_span.return_value = mock_span
    mock_context = Mock()

    with patch('monocle_apptrace.instrumentation.common.instrumentor.get_tracer', return_value=mock_tracer), \
         patch('monocle_apptrace.instrumentation.common.instrumentor.SpanHandler.set_default_monocle_attributes') as mock_set_attrs, \
         patch('monocle_apptrace.instrumentation.common.instrumentor.SpanHandler.set_workflow_properties') as mock_set_props, \
         patch('monocle_apptrace.instrumentation.common.instrumentor.SpanHandler.attach_workflow_type', return_value=mock_context) as mock_attach:

        token = start_trace()
        assert token == mock_context
        mock_tracer.start_span.assert_called_once()
        mock_set_attrs.assert_called_once()
        mock_set_props.assert_called_once()
        mock_attach.assert_called_once()

def test_stop_trace():
    mock_token = Mock()
    mock_span = Mock()
    mock_context = Mock()
    mock_context.get.return_value = mock_span

    with patch('monocle_apptrace.instrumentation.common.instrumentor.get_current', return_value=mock_context), \
         patch('monocle_apptrace.instrumentation.common.instrumentor.SpanHandler.detach_workflow_type') as mock_detach:

        stop_trace(mock_token)
        mock_span.end.assert_called_once()
        mock_detach.assert_called_once_with(mock_token)

def test_start_scope():
    scope_name = "test_scope"
    scope_value = "test_value"
    mock_token = Mock()

    with patch('monocle_apptrace.instrumentation.common.instrumentor.set_scope') as mock_set_scope:
        mock_set_scope.return_value = mock_token
        token = start_scope(scope_name, scope_value)
        assert token == mock_token
        mock_set_scope.assert_called_with(scope_name, scope_value)

def test_monocle_trace_scope():
    scope_name = "test_scope"
    scope_value = "test_value"
    mock_token = Mock()

    with patch('monocle_apptrace.instrumentation.common.instrumentor.start_scope') as mock_start_scope, \
         patch('monocle_apptrace.instrumentation.common.instrumentor.stop_scope') as mock_stop_scope:
        mock_start_scope.return_value = mock_token

        with monocle_trace_scope(scope_name, scope_value):
            pass

        mock_start_scope.assert_called_with(scope_name, scope_value)
        mock_stop_scope.assert_called_once_with(mock_token)

def test_monocle_trace_scope_method():
    scope_name = "test_scope"
    mock_token = Mock()

    @monocle_trace_scope_method(scope_name)
    def test_func():
        return "result"

    with patch('monocle_apptrace.instrumentation.common.instrumentor.start_scope') as mock_start_scope, \
         patch('monocle_apptrace.instrumentation.common.instrumentor.stop_scope') as mock_stop_scope:
        mock_start_scope.return_value = mock_token

        result = test_func()
        assert result == "result"
        mock_start_scope.assert_called_with(scope_name)
        mock_stop_scope.assert_called_once_with(mock_token)

@pytest.mark.asyncio
async def test_monocle_trace_scope_method_async():
    scope_name = "test_scope"

    @monocle_trace_scope_method(scope_name)
    async def test_async_func():
        return "async_result"

    with patch('monocle_apptrace.instrumentation.common.instrumentor.async_wrapper') as mock_async_wrapper:
        mock_async_wrapper.return_value = "async_result"
        result = await test_async_func()
        assert result == "async_result"

def test_monocle_trace_http_route():
    @monocle_trace_http_route
    def test_route():
        return "route_result"

    with patch('monocle_apptrace.instrumentation.common.instrumentor.http_route_handler') as mock_handler:
        mock_handler.return_value = "route_result"
        result = test_route()
        assert result == "route_result"

@pytest.mark.asyncio
async def test_monocle_trace_http_route_async():
    @monocle_trace_http_route
    async def test_async_route():
        return "async_route_result"

    with patch('monocle_apptrace.instrumentation.common.instrumentor.http_async_route_handler') as mock_handler:
        mock_handler.return_value = "async_route_result"
        result = await test_async_route()
        assert result == "async_route_result"

def test_fixed_id_generator():
    trace_id = 12345
    generator = FixedIdGenerator(trace_id)

    assert generator.generate_trace_id() == trace_id
    assert isinstance(generator.generate_span_id(), int)
    assert 0 <= generator.generate_span_id() < 2**64
