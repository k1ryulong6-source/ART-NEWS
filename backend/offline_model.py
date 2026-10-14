"""Pinned, hash-verified multilingual MT weights. No inference API or key."""
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.request import urlopen
from .storage import ROOT


def configuration():
    return json.loads((ROOT / 'config/automation.json').read_text(encoding='utf-8'))


def provider_name():
    cfg = configuration()
    return 'offline-m2m100:' + cfg['model_revision'] + ':v1'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for part in iter(lambda: file.read(1 << 20), b''):
            digest.update(part)
    return digest.hexdigest()


def ensure_model(directory):
    cfg = configuration()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for filename, expected in cfg['model_files'].items():
        path = directory / filename
        if path.is_file() and sha256(path) == expected:
            continue
        temporary = directory / (filename + '.download')
        url = f"https://huggingface.co/{cfg['model_repository']}/resolve/{cfg['model_revision']}/{filename}"
        with urlopen(url, timeout=120) as response, temporary.open('wb') as output:
            for chunk in iter(lambda: response.read(1 << 20), b''):
                output.write(chunk)
        if sha256(temporary) != expected:
            temporary.unlink()
            raise ValueError('model_checksum_mismatch:' + filename)
        temporary.replace(path)
    return directory


class OfflineTranslator:
    name = provider_name()

    def __init__(self, directory=None):
        # Imported only in the translation job, never during static builds/tests.
        import ctranslate2
        import sentencepiece
        directory = ensure_model(directory or ROOT / 'runtime/models/m2m100-int8')
        self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(directory / 'sentencepiece.bpe.model'))
        self.model = ctranslate2.Translator(str(directory), device='cpu', compute_type='int8',
                                          inter_threads=1, intra_threads=min(4, os.cpu_count() or 1))

    def split(self, text):
        # Split original strings, not decoded token slices: every source
        # character, punctuation mark and number remains represented.
        cap = configuration()['max_source_tokens']
        result = []
        while text:
            low, high = 1, min(len(text), cap * 8)
            while low < high:
                mid = (low + high + 1) // 2
                if len(self.tokenizer.encode(text[:mid])) <= cap:
                    low = mid
                else:
                    high = mid - 1
            end = low
            if end < len(text):
                boundary = max(text.rfind(mark, 0, end) for mark in ('。', '！', '？', '. ', '! ', '? ', '\n', ' '))
                if boundary > end // 2:
                    end = boundary + 1
            result.append(text[:end])
            text = text[end:]
        return result

    def translate_plain(self, text, language):
        if language not in configuration()['supported_languages']:
            raise ValueError('unsupported_language:' + language)
        source = ['__' + language + '__'] + self.tokenizer.encode(text, out_type=str) + ['</s>']
        result = self.model.translate_batch([source], target_prefix=[['__zh__']],
                                           beam_size=2, max_decoding_length=512)[0]
        tokens = result.hypotheses[0]
        if len(tokens) >= 512:
            raise ValueError('translation_truncated')
        return self.tokenizer.decode([token for token in tokens if token not in ('__zh__', '</s>', '<s>')]).strip()

    def translate(self, text, language):
        from .editorial import numbers
        result = self.translate_plain(text, language)
        if numbers(text) <= numbers(result):
            return result
        # MT sometimes drops numeric artwork/film titles in parentheses.
        # Translate surrounding prose while retaining literal numeric phrases
        # and URLs, rather than publishing a missing date, price or work code.
        literal = re.compile(r'\([^()\n]{0,160}\d[^()\n]{0,160}\)|https?://[^\s]+|[$€£¥]?\d+(?:[,:./]\d+)*(?:\s*(?:million\b|billion\b|thousand\b|万|亿))?', re.I)
        output, offset = [], 0
        for match in literal.finditer(text):
            prose = text[offset:match.start()]
            if prose.strip():
                output.append(self.translate_plain(prose, language))
            output.append(match.group())
            offset = match.end()
        prose = text[offset:]
        if prose.strip():
            output.append(self.translate_plain(prose, language))
        return ''.join(output) if output else result
