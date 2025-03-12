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
    monocle_trace_scope,
    monocle_trace_scope_method,
    monocle_trace_http_route,
    FixedIdGenerator
)
from monocle_apptrace.instrumentation.common.span_handler import SpanHandler
from monocle_apptrace.instrumentation.common.wrapper_method import WrapperMethod

@pytest.fixture
def mock_tracer():
    return Mock()

@pytest.fixture
def mock_span():
    return Mock()

@pytest.fixture
def mock_context():
    return Mock()

def test_get_instrumentor(mock_tracer):
    instrumentor = MonocleInstrumentor(handlers={})
    wrapper = instrumentor.get_instrumentor(mock_tracer)

    async def test_fn():
        return "test"

    wrapped = wrapper({}, None, "test_span", None, test_fn)
    assert callable(wrapped)

def test_instrumentation_dependencies():
    instrumentor = MonocleInstrumentor(handlers={})
    deps = instrumentor.instrumentation_dependencies()
    assert isinstance(deps, tuple)
    assert len(deps) == 0

@patch('monocle_apptrace.instrumentation.common.instrumentor.trace')
@patch('monocle_apptrace.instrumentation.common.instrumentor.get_monocle_exporter')
def test_setup_monocle_telemetry(mock_exporter, mock_trace):
    mock_exporter.return_value = [Mock()]
    mock_trace.get_tracer_provider.return_value = Mock()

    result = setup_monocle_telemetry(
        workflow_name="test_workflow",
        span_processors=[Mock(spec=SpanProcessor)],
        span_handlers={},
        wrapper_methods=[{"package": "test"}]
    )

    assert isinstance(result, MonocleInstrumentor)

def test_on_processor_start(mock_span):
    context_props = {"test_key": "test_value"}
    with patch('monocle_apptrace.instrumentation.common.instrumentor.get_value') as mock_get:
        mock_get.return_value = context_props
        on_processor_start(mock_span, None)
        mock_span.set_attribute.assert_called_with("session.test_key", "test_value")

@patch('monocle_apptrace.instrumentation.common.instrumentor.get_tracer')
@patch('monocle_apptrace.instrumentation.common.instrumentor.get_tracer_provider')
def test_start_trace(mock_provider, mock_get_tracer):
    mock_tracer = Mock()
    mock_span = Mock()
    mock_tracer.start_span.return_value = mock_span
    mock_get_tracer.return_value = mock_tracer

    token = start_trace()
    assert token is not None
    mock_span.end.assert_not_called()

@patch('monocle_apptrace.instrumentation.common.instrumentor.get_current')
def test_stop_trace(mock_get_current):
    mock_span = Mock()
    mock_context = Mock()
    mock_context.get.return_value = mock_span
    mock_get_current.return_value = mock_context

    token = Mock()
    stop_trace(token)
    mock_span.end.assert_called_once()

@pytest.mark.asyncio
async def test_monocle_trace_scope():
    async with monocle_trace_scope("test_scope", "test_value"):
        pass

@pytest.mark.asyncio
async def test_monocle_trace_scope_method():
    @monocle_trace_scope_method("test_scope")
    async def test_fn():
        return "test"

    result = await test_fn()
    assert result == "test"

@pytest.mark.asyncio
async def test_monocle_trace_http_route():
    @monocle_trace_http_route
    async def test_route():
        return "test"

    result = await test_route()
    assert result == "test"

def test_fixed_id_generator():
    gen = FixedIdGenerator(123)
    trace_id = gen.generate_trace_id()
    span_id = gen.generate_span_id()

    assert trace_id == 123
    assert isinstance(span_id, int)
