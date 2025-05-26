from app.face_processor_service import FaceProcessorService


def main():
    """Main application entry point"""
    import cv2
    from app.database import SessionLocal
    from app.repositories import get_repositories

    # Create database session
    db = SessionLocal()

    try:
        # Initialize face processor service
        data_path = "face/model/face_id/data_face/"
        service = FaceProcessorService(db, recognition_attempts=3, data_path=data_path)

        print("Processing video...")

        # Get unprocessed frames
        repos = get_repositories(db)
        video_frame_repo = repos["video_frame"]
        saved_frames = video_frame_repo.get_unprocessed_frames()

        for saved_frame in saved_frames:
            frame = cv2.imread(saved_frame['frame_path'])

            if frame is None:
                continue

            # Process frame using service
            success = service.process_frame(frame)

            if success:
                # Mark frame as processed
                video_frame_repo.mark_as_processed(saved_frame['id'])

            # Check for exit condition
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        db.close()


if __name__ == "__main__":
    main()