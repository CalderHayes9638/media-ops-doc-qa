"""Run once to load the sample runbooks into the collection the service queries."""
from __future__ import annotations

from asset_library import DocChunk, ensure_collection, index

DOCS = [
    DocChunk("ingest-01", "ingest", "Mezzanine intake",
             "Mezzanine files land in the intake bucket as ProRes 422 HQ. Anything above 4K is "
             "split into 30 minute reels before a job is queued."),
    DocChunk("ingest-02", "ingest", "Rejected uploads",
             "An upload is rejected when audio loudness is outside -24 to -22 LUFS. The uploader "
             "gets one automatic retry slot within 24 hours."),
    DocChunk("proc-01", "processing", "Transcode ladder",
             "The ladder renders 1080p, 720p and 480p HLS renditions. A job that exceeds 90 minutes "
             "of wall clock is retried once on the large worker pool."),
    DocChunk("proc-02", "processing", "Job retries",
             "Processing jobs retry twice with exponential backoff. After the second retry the job "
             "moves to the manual review queue and the owning producer is notified."),
    DocChunk("deliv-01", "delivery", "Creator delivery windows",
             "Finished renditions are published to creators in the 06:00-10:00 local window. Signed "
             "download links stay valid for 72 hours."),
    DocChunk("deliv-02", "delivery", "Takedowns",
             "A takedown request pulls every rendition within 15 minutes and marks the asset "
             "unavailable for delivery until a producer clears it."),
]


if __name__ == "__main__":
    ensure_collection()
    count = index(DOCS)
    print(f"indexed {count} passages into the media-ops collection")
