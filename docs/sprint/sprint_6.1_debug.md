SOLUTION SUMMARY
Problem: Jobs stuck in feature_extraction phase because:

Vision-embedding service not processing video frames (0/12 videos have embeddings)
Vision-keypoint service publishing events with job_id=unknown instead of correct job ID
Impact: All jobs with videos will be stuck indefinitely in feature_extraction phase

Next Steps:

Fix the job_id=unknown issue in vision-keypoint service
Investigate why vision-embedding service isn't processing video frames
Manually fix the current stuck job by simulating the missing events
The debugging tools I created will help monitor and fix similar issues in the future. The root cause is in the video processing services, not the phase transition logic itself.
-------------------------
The video-crawler is publishing videos.keyframes.ready events without the job_id field. It only includes video_id and frames, but the vision services need the job_id to track progress.