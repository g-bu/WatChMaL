"""
Class implementing a PMT dataset for CNNs in h5 format
Modified from mPMT dataset for use with single PMTs
"""

# torch imports
from torch import from_numpy

# generic imports
import numpy as np

# WatChMaL imports
from watchmal.dataset.h5_dataset import H5Dataset
from watchmal.dataset.cnn_mpmt import transformations
import watchmal.dataset.data_utils as du

class CNNDataset(H5Dataset):
    def __init__(self, h5file, pmt_positions_file, is_distributed, transforms=None, collapse_arrays=False):
        """
        Args:
            h5_path             ... path to h5 dataset file
            is_distributed      ... whether running in multiprocessing mode
            transforms          ... transforms to apply
            collapse_arrays     ... whether to collapse arrays in return
        """
        super().__init__(h5file, is_distributed)
        
        self.pmt_positions = np.load(pmt_positions_file)['pmt_image_positions']
        self.data_size = np.max(self.pmt_positions, axis=0) + 1
        self.barrel_rows = [row for row in range(self.data_size[0]) if
                            np.count_nonzero(self.pmt_positions[:,0] == row) == self.data_size[1]]
        self.data_size = np.insert(self.data_size, 0, 1)
        self.collapse_arrays = collapse_arrays
        self.transforms = None #du.get_transformations(transformations, transforms)

    def process_data(self, hit_pmts, hit_data):
        """
        Returns event data from dataset associated with a specific index

        Args:
            hit_pmts                ... array of ids of hit pmts
            hid_data                ... array of data associated with hits
        
        Returns:
            data                    ... array of hits in cnn format
        """
        hit_pmts -= 1 #SK cable numbers start at 1

        hit_rows = self.pmt_positions[hit_pmts, 0]
        hit_cols = self.pmt_positions[hit_pmts, 1]

        data = np.zeros(self.data_size)
        data[0, hit_rows, hit_cols] = hit_data

        # fix barrel array indexing to match endcaps in xyz ordering
        #barrel_data = data[:, self.barrel_rows, :]
        #data[:, self.barrel_rows, :] = barrel_data[barrel_map_array_idxs, :, :]

        # collapse arrays if desired
        if self.collapse_arrays:
            data = np.expand_dims(np.sum(data, 0), 0)
        
        return data

    def  __getitem__(self, item):

        data_dict = super().__getitem__(item)

        processed_data = from_numpy(self.process_data(self.event_hit_pmts, self.event_hit_charges))
        processed_data = du.apply_random_transformations(self.transforms, processed_data)

        data_dict["data"] = processed_data

        return data_dict

    def retrieve_event_data(self, item):
        """
        Returns event data from dataset associated with a specific index

        Args:
            item                    ... index of event

        Returns:
            hit_pmts                ... array of ids of hit pmts
            pmt_charge_data         ... array of charge of hits
            pmt_time_data           ... array of times of hits

        """
        data_dict = super().__getitem__(item)

        # construct charge data with barrel array indexing to match endcaps in xyz ordering
        pmt_charge_data = self.process_data(self.event_hit_pmts, self.event_hit_charges).flatten()

        # construct time data with barrel array indexing to match endcaps in xyz ordering
        pmt_time_data = self.process_data(self.event_hit_pmts, self.event_hit_times).flatten()

        return self.event_hit_pmts, pmt_charge_data, pmt_time_data
