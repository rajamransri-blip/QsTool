import hashlib
import io
import struct
import zlib

from dataclasses import dataclass
from pathlib import Path


MAGIC = 0x5A6F12E1


class PakError(Exception):
    pass


@dataclass
class Entry:
    path: str
    offset: int
    compressed_size: int
    uncompressed_size: int
    sha1: bytes
    compression: str
    blocks: list


class Reader:

    def __init__(self, fp):
        self.fp = fp

    def raw(self, size):
        data = self.fp.read(size)

        if len(data) != size:
            raise PakError(
                "Unexpected EOF."
            )

        return data

    def i32(self):
        return struct.unpack(
            "<i",
            self.raw(4),
        )[0]

    def u32(self):
        return struct.unpack(
            "<I",
            self.raw(4),
        )[0]

    def i64(self):
        return struct.unpack(
            "<q",
            self.raw(8),
        )[0]

    def fstring(self):
        size = self.i32()

        if size == 0:
            return ""

        if size < 0:
            count = -size

            data = self.raw(
                count * 2
            )

            return data[:-2].decode(
                "utf-16le",
                errors="replace",
            )

        data = self.raw(size)

        return data[:-1].decode(
            "utf-8",
            errors="replace",
        )


class PakReader:

    def __init__(self, path):
        self.path = Path(path)
        self.version = None
        self.index_offset = None
        self.index_size = None
        self.encrypted_index = False
        self.entries = {}

    def open(self):
        size = (
            self.path.stat().st_size
        )

        if size < 64:
            raise PakError(
                "File is too small."
            )

        with self.path.open(
            "rb"
        ) as fp:

            tail_size = min(
                size,
                4096,
            )

            fp.seek(
                size - tail_size
            )

            tail = fp.read(
                tail_size
            )

            marker = struct.pack(
                "<I",
                MAGIC,
            )

            position = tail.rfind(
                marker
            )

            if position < 0:
                raise PakError(
                    "Unreal PAK magic "
                    "not found."
                )

            footer = (
                size
                - tail_size
                + position
            )

            fp.seek(footer)

            magic = struct.unpack(
                "<I",
                fp.read(4),
            )[0]

            if magic != MAGIC:
                raise PakError(
                    "Invalid PAK magic."
                )

            self.version = struct.unpack(
                "<I",
                fp.read(4),
            )[0]

            self.index_offset = (
                struct.unpack(
                    "<q",
                    fp.read(8),
                )[0]
            )

            self.index_size = (
                struct.unpack(
                    "<q",
                    fp.read(8),
                )[0]
            )

            index_hash = fp.read(
                20
            )

            if len(index_hash) != 20:
                raise PakError(
                    "Invalid footer."
                )

            flag = fp.read(1)

            self.encrypted_index = (
                bool(
                    flag
                    and flag[0] != 0
                )
            )

            if (
                self.index_offset < 0
                or self.index_size <= 0
            ):
                raise PakError(
                    "Invalid index."
                )

            if (
                self.index_offset
                + self.index_size
                > size
            ):
                raise PakError(
                    "Index outside PAK."
                )

            if self.encrypted_index:
                return self

            fp.seek(
                self.index_offset
            )

            index_data = fp.read(
                self.index_size
            )

        self.parse_index(
            index_data
        )

        return self

    def parse_index(
        self,
        data,
    ):
        reader = Reader(
            io.BytesIO(data)
        )

        mount = reader.fstring()

        count = reader.i32()

        if (
            count < 0
            or count > 50_000_000
        ):
            raise PakError(
                "Invalid entry count."
            )

        for _ in range(count):

            relative = (
                reader.fstring()
                .replace("\\", "/")
                .lstrip("/")
            )

            path = (
                mount + relative
            ).replace(
                "\\",
                "/",
            )

            offset = reader.i64()
            uncompressed = reader.i64()
            compressed = reader.i64()

            sha1 = reader.raw(
                20
            )

            block_count = (
                reader.i32()
            )

            if (
                block_count < 0
                or block_count > 1_000_000
            ):
                raise PakError(
                    "Invalid block count."
                )

            blocks = []

            for _block in range(
                block_count
            ):
                start = reader.i64()
                end = reader.i64()

                blocks.append(
                    (
                        start,
                        end,
                    )
                )

            compression_index = (
                reader.u32()
            )

            compression = {
                0: "none",
                1: "zlib",
                2: "gzip",
                3: "zstd",
            }.get(
                compression_index,
                f"method-{compression_index}",
            )

            self.entries[path] = Entry(
                path=path,
                offset=offset,
                compressed_size=compressed,
                uncompressed_size=uncompressed,
                sha1=sha1,
                compression=compression,
                blocks=blocks,
            )

    def read_entry(
        self,
        entry,
    ):
        with self.path.open(
            "rb"
        ) as fp:

            if entry.blocks:
                chunks = []

                for start, end in (
                    entry.blocks
                ):
                    if end < start:
                        raise PakError(
                            "Invalid block."
                        )

                    fp.seek(start)

                    chunks.append(
                        fp.read(
                            end - start
                        )
                    )

                raw = b"".join(
                    chunks
                )

            else:
                fp.seek(
                    entry.offset
                )

                raw = fp.read(
                    entry.compressed_size
                )

        if (
            entry.compression
            == "none"
        ):
            output = raw

        elif (
            entry.compression
            == "zlib"
        ):
            try:
                output = zlib.decompress(
                    raw
                )
            except zlib.error as exc:
                raise PakError(
                    f"Zlib error: {exc}"
                )

        elif (
            entry.compression
            == "gzip"
        ):
            try:
                output = zlib.decompress(
                    raw,
                    16
                    + zlib.MAX_WBITS,
                )
            except zlib.error as exc:
                raise PakError(
                    f"Gzip error: {exc}"
                )

        elif (
            entry.compression
            == "zstd"
        ):
            try:
                import zstandard
            except ImportError:
                raise PakError(
                    "Zstandard module is "
                    "not available in APK."
                )

            output = (
                zstandard
                .ZstdDecompressor()
                .decompress(raw)
            )

        else:
            raise PakError(
                "Unsupported compression: "
                + entry.compression
            )

        if (
            len(output)
            != entry.uncompressed_size
        ):
            raise PakError(
                "Uncompressed size mismatch."
            )

        digest = hashlib.sha1(
            output
        ).digest()

        if (
            entry.sha1
            and digest != entry.sha1
        ):
            raise PakError(
                "SHA1 verification failed."
            )

        return output
