import base64
import json
import re
import logging
import blackboxprotobuf

logger = logging.getLogger(__name__)

def convert_bytes_to_str(obj):
    """
    Recursively converts bytes to strings. 
    If decoding fails, returns a hex string representation.
    """
    if isinstance(obj, dict):
        return {key: convert_bytes_to_str(val) for key, val in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_str(item) for item in obj]
    elif isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except Exception:
            return f"hex:{obj.hex()}"
    return obj


def recursively_parse_nested_strings(obj):
    """
    Recursively look for serialized JSON strings (starting with '[' or '{') and parse them.
    This helps unpack double-serialized JSON data often found in Google Wiz payloads.
    Also automatically detects and decodes base64-encoded Protobuf payloads using blackboxprotobuf.
    """
    if isinstance(obj, list):
        return [recursively_parse_nested_strings(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: recursively_parse_nested_strings(val) for key, val in obj.items()}
    elif isinstance(obj, str):
        trimmed = obj.strip()
        # 1. Try parsing nested JSON strings
        if (trimmed.startswith('[') and trimmed.endswith(']')) or (trimmed.startswith('{') and trimmed.endswith('}')):
            try:
                parsed = json.loads(trimmed)
                return recursively_parse_nested_strings(parsed)
            except json.JSONDecodeError:
                # Not valid JSON, keep as string
                return obj
            except Exception as e:
                logger.debug(f"Failed to parse suspected nested JSON: {e}")
                return obj
        
        # 2. Try decoding as base64-encoded Protobuf
        if len(trimmed) > 8 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in trimmed):
            try:
                decoded_bytes = base64.b64decode(trimmed, validate=True)
                if len(decoded_bytes) > 4:
                    decoded_dict, typedef = blackboxprotobuf.decode_message(decoded_bytes)
                    clean_dict = convert_bytes_to_str(decoded_dict)
                    return {
                        "_type": "protobuf",
                        "data": clean_dict,
                        "typedef": typedef
                    }
            except Exception as e:
                # Not valid protobuf or base64 decoding failed
                logger.debug(f"Failed to decode base64 string as protobuf: {e}")
                pass
                
    return obj


class WizStreamParser:
    """
    Parses Google Wiz stream payloads chunk by chunk.
    Handles XSSI prefix stripping and size prefix splitting.
    """
    def __init__(self):
        self.buffer = ""
        self.parsed_chunks = []
        
    def feed(self, text, is_finished=False):
        self.buffer += text
        
        # Strip XSSI prefix if it's at the very start
        if self.buffer.startswith(")]}'"):
            self.buffer = self.buffer[4:].strip()
            
        # Split on size prefixes: a line containing only digits
        parts = re.split(r'(?:^|\r?\n)(\d+)\r?\n', self.buffer)
        num_pairs = (len(parts) - 1) // 2
        
        # If the stream is not finished yet, we only parse up to num_pairs - 1,
        # because the last chunk content parts[-1] might still be loading.
        # If the stream is finished, we can parse all pairs.
        limit = num_pairs if is_finished else (num_pairs - 1)
        
        new_chunks = []
        for i in range(len(self.parsed_chunks), limit):
            size_str = parts[1 + 2*i]
            content = parts[2 + 2*i]
            try:
                parsed = json.loads(content)
                parsed = recursively_parse_nested_strings(parsed)
                self.parsed_chunks.append(parsed)
                new_chunks.append(parsed)
                logger.info(f"Successfully parsed stream chunk {i} (size prefix: {size_str})")
            except Exception as e:
                # Keep raw as fallback and log the warning
                fallback = {"raw": content, "error": str(e)}
                self.parsed_chunks.append(fallback)
                new_chunks.append(fallback)
                logger.warning(f"Error parsing stream chunk {i} (size prefix: {size_str}): {e}")
        return new_chunks
