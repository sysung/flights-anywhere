import json
from app.scraper.stream_parser import WizStreamParser

def test_wiz_stream_parser_basic():
    parser = WizStreamParser()
    # Mock a basic Wiz stream: XSSI prefix + size prefix + json content
    raw_data = ")]}'\n10\n[\"test\", 123]"
    chunks = parser.feed(raw_data, is_finished=True)
    
    assert len(chunks) == 1
    assert chunks[0] == ["test", 123]

def test_wiz_stream_parser_incremental():
    parser = WizStreamParser()
    # First part of the stream
    parser.feed(")]}'\n10\n[\"first\"]", is_finished=False)
    # At this point, limit is num_pairs - 1 = 0, so no chunks are parsed yet
    assert len(parser.parsed_chunks) == 0
    
    # Second part of the stream
    parser.feed("\n11\n[\"second\"]", is_finished=True)
    # Now it's finished, it should parse both
    assert len(parser.parsed_chunks) == 2
    assert parser.parsed_chunks[0] == ["first"]
    assert parser.parsed_chunks[1] == ["second"]

def test_nested_json_parsing():
    parser = WizStreamParser()
    # Content with nested serialized JSON string
    nested_content = json.dumps(["parent", json.dumps(["child", 456])])
    raw_data = f"100\n{nested_content}"
    chunks = parser.feed(raw_data, is_finished=True)
    
    assert len(chunks) == 1
    # Should be recursively parsed
    assert chunks[0][0] == "parent"
    assert chunks[0][1][0] == "child"
    assert chunks[0][1][1] == 456
