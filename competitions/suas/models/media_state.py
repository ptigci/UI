"""What is on the camera's own card, and how the copy off it is going.

Two halves of one subject, so they are one object. The listing says what the
camera holds; the transfer says which of it is on its way here and how far
through. The page draws them side by side and the operator reads them as one
answer, so splitting them would only mean the panel holding two things that
always change together.

The third job is putting a file back together. A 4K still is several megabytes
over a shared 2.4 GHz link, so a file comes down in pieces and the pieces do not
have to arrive in order. Nothing is written to disk here: the finished bytes go
back to the caller with the file name on them, and where they land is the
caller's business.
"""

import base64

from competitions.suas.config import (
    KEY_CHUNK_COUNT,
    KEY_CHUNK_DATA,
    KEY_CHUNK_FILE_NAME,
    KEY_CHUNK_INDEX,
    KEY_MEDIA_FETCHED,
    KEY_MEDIA_FILES,
    KEY_MEDIA_KIND,
    KEY_MEDIA_NAME,
    KEY_MEDIA_PHOTO_COUNT,
    KEY_MEDIA_REASON,
    KEY_MEDIA_SIZE,
    KEY_MEDIA_VIDEO_COUNT,
    KEY_TRANSFER_BYTES_DONE,
    KEY_TRANSFER_BYTES_TOTAL,
    KEY_TRANSFER_FILES_DONE,
    KEY_TRANSFER_FILES_TOTAL,
    KEY_TRANSFER_FILE_NAME,
    KEY_TRANSFER_REASON,
    KEY_TRANSFER_SENDING_PHOTOS,
    KEY_TRANSFER_SENDING_VIDEOS,
    KEY_TRANSFER_STATE,
    KEY_TRANSFER_WATCHING,
    MEDIA_KIND_PHOTO,
    TRANSFER_STATE_COMPLETE,
    TRANSFER_STATE_FAILED,
    TRANSFER_STATE_FETCHING,
    TRANSFER_STATE_LISTING,
)

BYTES_PER_MEGABYTE = 1024 * 1024


class MediaFile:
    """One entry of the camera's listing."""

    def __init__(self, name: str, kind: str, size_bytes: int, fetched: bool) -> None:
        self.name = name
        self.kind = kind
        self.size_bytes = size_bytes
        self.fetched = fetched

    def is_photo(self) -> bool:
        return self.kind == MEDIA_KIND_PHOTO

    def megabytes(self) -> float:
        return self.size_bytes / BYTES_PER_MEGABYTE


class MediaLibraryState:
    """The card's contents, the copy in progress, and the file being rebuilt."""

    def __init__(self) -> None:
        self.files: list[MediaFile] = []
        self.photo_count = 0
        self.video_count = 0
        self.listing_reason: str = ""

        self.transfer_state: str = ""
        self.file_name: str = ""
        self.files_done = 0
        self.files_total = 0
        self.bytes_done = 0
        self.bytes_total = 0
        self.sending_photos = False
        self.sending_videos = False
        self.watching = False
        self.transfer_reason: str = ""

        self.collecting_name: str = ""
        self.collecting_count = 0
        self.collected_pieces: dict[int, bytes] = {}

    # The listing

    def update_list_from(self, payload: dict) -> None:
        """Take the aircraft's word on what the camera is holding."""
        entries = payload.get(KEY_MEDIA_FILES)
        if not isinstance(entries, list):
            entries = []
        self.files = [
            MediaFile(
                str(entry.get(KEY_MEDIA_NAME, "")),
                str(entry.get(KEY_MEDIA_KIND, "")),
                count_or_zero(entry.get(KEY_MEDIA_SIZE)),
                bool(entry.get(KEY_MEDIA_FETCHED)),
            )
            for entry in entries
            if isinstance(entry, dict)
        ]
        self.photo_count = count_or_zero(payload.get(KEY_MEDIA_PHOTO_COUNT))
        self.video_count = count_or_zero(payload.get(KEY_MEDIA_VIDEO_COUNT))
        self.listing_reason = payload.get(KEY_MEDIA_REASON) or ""

    def has_files(self) -> bool:
        return bool(self.files)

    # The copy

    def update_transfer_from(self, payload: dict) -> None:
        """Take the aircraft's word on the copy off the card."""
        self.transfer_state = payload.get(KEY_TRANSFER_STATE) or ""
        self.file_name = payload.get(KEY_TRANSFER_FILE_NAME) or ""
        self.files_done = count_or_zero(payload.get(KEY_TRANSFER_FILES_DONE))
        self.files_total = count_or_zero(payload.get(KEY_TRANSFER_FILES_TOTAL))
        self.bytes_done = count_or_zero(payload.get(KEY_TRANSFER_BYTES_DONE))
        self.bytes_total = count_or_zero(payload.get(KEY_TRANSFER_BYTES_TOTAL))
        self.sending_photos = bool(payload.get(KEY_TRANSFER_SENDING_PHOTOS))
        self.sending_videos = bool(payload.get(KEY_TRANSFER_SENDING_VIDEOS))
        self.watching = bool(payload.get(KEY_TRANSFER_WATCHING))
        self.transfer_reason = payload.get(KEY_TRANSFER_REASON) or ""

    def is_listing(self) -> bool:
        return self.transfer_state == TRANSFER_STATE_LISTING

    def is_fetching(self) -> bool:
        return self.transfer_state == TRANSFER_STATE_FETCHING

    def is_complete(self) -> bool:
        return self.transfer_state == TRANSFER_STATE_COMPLETE

    def is_failed(self) -> bool:
        return self.transfer_state == TRANSFER_STATE_FAILED

    def knows_the_size(self) -> bool:
        """Whether the aircraft has said how much there is to copy.

        It cannot until it has read the card, and a watch that copies frames as
        they are taken never has an end at all — which is what tells a bar that
        can fill from one that can only spin.
        """
        return self.bytes_total > 0

    def megabytes_done(self) -> float:
        return self.bytes_done / BYTES_PER_MEGABYTE

    def megabytes_total(self) -> float:
        return self.bytes_total / BYTES_PER_MEGABYTE

    # The file being put back together

    def add_chunk(self, payload: dict):
        """Collect one piece of a file, and hand back the file once it is whole.

        Returns (file_name, data) on the piece that completes the file and None
        on every other one. A piece that arrives twice replaces itself, pieces
        that arrive out of order are put in order at the end, and a piece of a
        different file starts the collection again — the aircraft sends one file
        at a time, so a new name means the last one is not coming.
        """
        file_name = payload.get(KEY_CHUNK_FILE_NAME) or ""
        chunk_index = count_or_zero(payload.get(KEY_CHUNK_INDEX))
        chunk_count = count_or_zero(payload.get(KEY_CHUNK_COUNT))

        if file_name != self.collecting_name or chunk_count != self.collecting_count:
            self.collecting_name = file_name
            self.collecting_count = chunk_count
            self.collected_pieces = {}

        self.collected_pieces[chunk_index] = base64.b64decode(
            payload.get(KEY_CHUNK_DATA) or ""
        )

        if sorted(self.collected_pieces) != list(range(chunk_count)):
            return None

        whole_file = b"".join(
            self.collected_pieces[index] for index in range(chunk_count)
        )
        self.collecting_name = ""
        self.collecting_count = 0
        self.collected_pieces = {}
        return file_name, whole_file


def count_or_zero(value) -> int:
    """A count from the wire, or zero when the field is missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
