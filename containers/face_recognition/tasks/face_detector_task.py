from ship.core.base_task import BaseTask
from ship.setting import absolute_path


class FaceDetectorTask(BaseTask):
    def run(self, frame, thresh=0.8, do_flip=False):
        from face.model.retinaface.retinaface import RetinaFace

        # Инициализация детектора один раз, на GPU (gpuid=0)
        GPUID = 0
        DETECTOR = RetinaFace(absolute_path('face/checkpoint/R50/R50'), 0, GPUID, 'net3')

        return DETECTOR.detect(frame, thresh, scales=[1.0], do_flip=do_flip)
