1. The BECA-D dataset provides a comprehensive dataset for cattle back re-identification.
    The data is divided into a training set and a validation set, containing 16,083 images of 5,361 individual cows in the training set, and 806 images of 300 cows in the validation set. 
    The validation set includes 712 positive sample pairs and 712 randomly selected negative sample pairs.
    Each image filename includes two components: the first element is the cow ID, and the second is the image index under that ID.

2. The BECA-L dataset provides data for both object detection and re-identification processes.

    In the object detection folder, there are 8,321 original captured images along with a JSON annotation file. The JSON file follows the COCO format and includes the following annotations:
    Object detection annotations in 'xyxy' format, Oriented bounding box (OBB) annotations in 'xyxyangle' format, consistent with the HRSC dataset specification, Pose estimation keypoint annotations.
    The annotation specifications are as follows:
        The annotations.json file contains both image information and annotation details. The "annotations" section includes object-level annotations such as axis-aligned bounding boxes (AABBs), oriented bounding boxes (OBBs), and keypoints.
        The obb_output folder contains results where OBB annotations are overlaid on the original images and cropped accordingly.

    In the re-identification folder, there are four subfolders: cowshed0, cowshed2, cowshed3, and cowshed_sum. These respectively contain re-identification images from cowshed 0, cowshed 2, cowshed 3, and a consolidated set of re-identification images.
    Note: The images in cowshed_sum have been reordered, which is different from the datasets in the other cowshed folders.
    Each image filename includes labeling information, consisting of the cow ID, date of capture, cowshed index, and the cows relative position to the camera at the time of capture, represented as [0,1].