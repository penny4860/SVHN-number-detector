#-*- coding: utf-8 -*-

import cv2
import object_detector.utils as utils
import object_detector.file_io as file_io
import numpy as np
import random

import numpy as np
import os

class FeatureExtractor():
    
    def __init__(self, descriptor, patch_size, data_file):
        self._desc = descriptor
        self._patch_size = patch_size
        
        if data_file is None:
            self._dataset = []
        else:
            self._dataset = file_io.FileHDF5().read(data_file, "label_and_features").tolist()
    
    # Todo : Template Method Pattern??
    def add_positive_sets(self, image_dir, pattern, annotation_path, sample_ratio=1.0, padding=5, augment=True, label=1):
        
        features_set = []
        image_files = self._get_image_files(image_dir, pattern, sample_ratio)
    
        for image_file in image_files:
            image = cv2.imread(image_file)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image_id = utils.get_file_id(image_file)
            
            annotation_file = "{}/annotation_{}.mat".format(annotation_path, image_id)
            bb = file_io.FileMat().read(annotation_file)["box_coord"][0]
            roi = utils.crop_bb(image, bb, padding=padding, dst_size=self._patch_size)
            
            patches = (roi, cv2.flip(roi, 1)) if augment else (roi,)
            
            # Todo : augment modulization
            features = self._desc.describe(patches)
            features_set += features.tolist()
            
        labels = np.zeros((len(features_set), 1)) + label
        dataset = np.concatenate([labels, np.array(features_set)], axis=1)
        self._dataset += dataset.tolist()


    def add_negative_sets(self, image_dir, pattern, n_samples_per_img, sample_ratio=1.0):
        # Todo : progressbar
        # Todo : 한꺼번에 write 하지말고, 10개 이미지를 모아서 write 를 자주하는 방식으로 수정
        
        features_set = []
        image_files = self._get_image_files(image_dir, pattern, sample_ratio)

        for image_file in image_files:
            image = cv2.imread(image_file)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
             
            patches = utils.crop_random(image, self._patch_size, n_samples_per_img)
             
            features = self._desc.describe(patches)
            features_set += features.tolist()

        labels = np.zeros((len(features_set), 1))
        dataset = np.concatenate([labels, np.array(features_set)], axis=1)
        self._dataset += dataset.tolist()
        
    def add_data(self, features, label):
        labels = np.zeros((len(features), 1)) + label
        dataset = np.concatenate([labels, features], axis=1)

        self._dataset += dataset.tolist()
    
    def save(self, data_file):
        file_io.FileHDF5().write(np.array(self._dataset), data_file, "label_and_features")

    def summary(self):
        
        labels = np.array(self._dataset)[:, 0]
        feature_shape = np.array(self._dataset)[:, 1:].shape
        
        n_positive_samples = len(labels[labels > 0])
        n_negative_samples = len(labels[labels == 0])
        n_hard_negative_samples = len(labels[labels == -1])
                                 
        print "[FeatureGetter INFO] Positive samples: {}, Negative samples: {}, Hard Negative Mined samples: {}".format(n_positive_samples, n_negative_samples, n_hard_negative_samples)
        print "[FeatureGetter INFO] Feature Dimension: {}".format(feature_shape[1])

    def get_dataset(self, include_hard_negative=True):
        if self._dataset is None:
            raise ValueError('There is no dataset in this instance')
        else:
            dataset = np.array(self._dataset)
            if include_hard_negative:
                dataset[dataset[:,0] < 0, 0] = 0
            else:
                dataset = dataset[dataset[:,0] >= 0]
            return dataset
    
    def _get_image_files(self, directory, pattern, sample_ratio):
        image_files = file_io.list_files(directory, pattern)
        image_files = random.sample(image_files, int(len(image_files) * sample_ratio))
        return image_files


class SVHNFeatureExtractor(FeatureExtractor):
    # Todo : Template Method Pattern??
    def add_positive_sets(self, annotation_file, sample_ratio=1.0, padding=5, augment=True, label=1):
        
        features_set = []
        labels_set = []
        image_path = os.path.split(annotation_file)[0]
        annotations = file_io.FileJson().read(annotation_file)
        annotations = annotations[:int(len(annotations)*sample_ratio)]

        for annotation in annotations:
            image = cv2.imread(os.path.join(image_path, annotation["filename"]))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)    
            
            patches = []
            labels = []
            for box in annotation["boxes"]:
                x1 = int(box["left"])
                y1 = int(box["top"])
                w = int(box["width"])
                h = int(box["height"])

                bb = (y1, y1+h, x1, x1+w)
                label = int(box["label"])
                
                roi = utils.crop_bb(image, bb, padding=padding, dst_size=self._patch_size)
                patches.append(roi)
                labels.append(label)

            # Todo : augment modulization
            features = self._desc.describe(patches)
            features_set += features.tolist()
            labels_set += labels
            
        #labels = np.zeros((len(features_set), 1)) + label
        dataset = np.concatenate([np.array(labels_set).reshape(-1, 1), np.array(features_set)], axis=1)
        self._dataset += dataset.tolist()

    

