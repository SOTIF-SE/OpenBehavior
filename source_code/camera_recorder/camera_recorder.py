import re
import carla
import numpy as np
import cv2
import os

class CameraRecorder(object):
    def __init__(self, world, ego_vehicle, path):
        self.world = world
        self.video_path = path
        self.ego_vehicle = ego_vehicle
        self.video_writer = None
        self.camera = None

    def start(self):
        self.init_camera()
        self.camera.listen(self.camera_callback)

    def init_camera(self):
        bp_lib = self.world.get_blueprint_library()
        camera_bp = bp_lib.find("sensor.camera.rgb")

        camera_bp.set_attribute("image_size_x", "1280")
        camera_bp.set_attribute("image_size_y", "720")
        camera_bp.set_attribute("fov", "90")

        camera_transform = carla.Transform(
            carla.Location(x=-8, z=5),
            carla.Rotation(pitch=-20.0)
        )

        self.camera = self.world.spawn_actor(
            camera_bp,
            camera_transform,
            attach_to=self.ego_vehicle
        )

    def camera_callback(self, image):
        img = np.frombuffer(image.raw_data, dtype=np.uint8)
        img = img.reshape((image.height, image.width, 4))
        img = img[:, :, :3]
        if self.video_writer is None:
            match = re.search(r"generation_(\d+)/ind_(\d+)\.json", self.video_path)
            gen_value = int(match.group(1))
            idx_value = int(match.group(2))
            os.makedirs("traffic_accident_video", exist_ok=True)
            self.video_writer = cv2.VideoWriter(
                "traffic_accident_video/ego_accident_{}_{}.avi".format(gen_value, idx_value),
                cv2.VideoWriter_fourcc(*'XVID'),
                20,
                (image.width, image.height)
            )

        self.video_writer.write(img)

    def stop_camera(self):
        if self.camera:
            self.camera.stop()
            self.camera.destroy()
        if self.video_writer:
            self.video_writer.release()

