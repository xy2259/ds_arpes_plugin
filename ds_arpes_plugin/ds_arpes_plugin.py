import argparse

import numpy as np
from arpys import dl, pp
from data_slicer import cmaps, plugin

class DatasetError(Exception) :
    """ Error raised when the type of data found does not conform to our 
    expectations.
    """
    pass

class ARPES_Plugin(plugin.Plugin) :
    """ A plugin which connects the analysis functionalities of the `aprys` 
    module with PIT.
    """

    _message = 'No ARPES data has been found. Load data with `load_data()`.'
    filename = '<missing filename>'

    def __init__(self, *args, **kwargs) :
        super().__init__(*args, **kwargs)
        self.name = 'ARPES plugin'
        self.shortname = 'arpes'

        # Make arpys module accessible
        self.dl = dl
        self.pp = pp

    def load_data(self, filename) :
        """ Load a set of ARPES data and bring it into PIT-friendly form. 
        Also return the arpys data Namespace for inspection.
        """
        # Retrieve the data in arpys format and store it
        D = dl.load_data(filename)
        self.D = D

        # Set the loaded data in PIT
        self.data_handler.prepare_data(D.data, [D.zscale, D.yscale, D.xscale])

        self.filename = filename

        return D

    def load(self, filename) :
        """ Load a set of ARPES data and bring it into PIT-friendly form. 
        Also return the arpys data Namespace for inspection.

        This is a convenience alias for :func: `load_data 
        <ds_arpes_plugin.ARPES_Plugin.load_data`.
        """
        return self.load_data(filename)

    def open(self, filename) :
        """ Load a set of ARPES data and bring it into PIT-friendly form. 
        Also return the arpys data Namespace for inspection.

        This is a convenience alias for :func: `load_data 
        <ds_arpes_plugin.ARPES_Plugin.load_data`.
        """
        return self.load_data(filename)

    def _check_for_arpes_data(self) :
        """ Check if ARPES data has been loaded or raise an exception. """
        if not hasattr(self, 'D') :
            raise DatasetError(self._message)

    def a2k(self, alpha_axis, beta_axis=None, dalpha=0, dbeta=0, 
            orientation='horizontal', work_func=4, units=0, hv=None) :
        """ Convert the axes from angles to k-space. 
        This updates the selected axes in the `pit.axes` and makes the change 
        visible in the main plot.
        Notice that there will be no error message or anything if you happen 
        to select nonsensical axes for *alpha_axis* and *beta_axis*, so 
        check carefully if your result makes sense.
        
        *Parameters*
        ===========  ===========================================================
        alpha_axis   int; index of the axis containing the angles along the 
                     analyser slit. In PIT, 0 corresponds to the horizontal 
                     axis of the main plot, 1 to its vertical axis and 2 to 
                     the remaining 3rd axis.
        beta_axis    int or None; index of the axis containing the angles 
                     perpendicular to the analyser slit. Can be left out 
                     (i.e. set to *None*) to only transform 1 axis. A 
                     constant value for the respective angle can then be 
                     specified with *dbeta*.
        dalpha       float; angular offset along *alpha*.
        dbeta        float; angular offset along *beta* or, if *beta_axis* is 
                     *None*, the value of *beta*.
        orientation  str, must start with 'h' or 'v'; specifies the analyzer 
                     slit geometry (horizontal or vertical).
        work_func    float; work function in eV.
        units        float; toggle what units to use.
                     - 0 corresponds to inverse Angstrom
                     - any nonzero value corresponds to units of pi/*units*
                       (this is useful, e.g. to convert to units of 
                       pi/lattice_constant)
        ===========  ===========================================================

        *Returns*
        ==  ====================================================================
        KX  array of shape (nkx, nky); mesh of k values in parallel direction in 
            units of inverse Angstrom.
        KY  array of shape (nkx, nky); mesh of k values in perpendicular 
            direction in units of inverse Angstrom.
        ==  ====================================================================
        """
        self._check_for_arpes_data()

        # Fetch correct axes
        axes = self.data_handler.original_axes
        i = self.data_handler._roll_state
        axes = np.roll(axes, -i)
        alpha = axes[alpha_axis]
        if beta_axis is not None :
            beta = axes[beta_axis]
        else :
            beta = np.array([0])

        if hv is None : hv = self.D.hv

        # Convert angles to k-space
        KX, KY = pp.angle_to_k(alpha, beta, hv, dalpha=dalpha, dbeta=dbeta, 
                               orientation=orientation, work_func=work_func)
        
        if units!=0 :
            KX /= (np.pi/units)
            KY /= (np.pi/units)

        # Update PIT
        new_alpha = KY[:,0]
        self.data_handler.axes[alpha_axis] = new_alpha
        if beta_axis is not None :
            new_beta = KX[0]
            self.data_handler.axes[beta_axis] = new_beta

        # Reset all unaffected axes (necessary when several a2k runs with 
        # different axes are executed)
        for i in range(3) :
            if i not in [alpha_axis, beta_axis] :
                self.data_handler.axes[i] = axes[i]

        # Update the axes visually
        self.main_window.set_axes()

        return KX, KY

    def main_plot_normalize_per_segment(self, dim=0, min=False) :
        """ Apply :func: `normalize_per_segment 
        <arpys.postprocessing.normalize_per_segment>` to the data in the 
        main_plot and visualize the result. 

        :Note:
        This result is not stored, does not affect other plots (like cut_plot 
        and the x- and y-plots) and is lost the next time the main_plot is 
        updated by any means.
        To create a more persisting result, see :func: `normalize_per_segment 
        <ds_arpes_plugin.ARPES_Plugin.normalize_per_segment>`
        """
        data = self.main_window.main_plot.image_data
        norm_data = pp.normalize_per_segment(data, dim=dim)
        self.main_window.set_image(norm_data, emit=False)

    def cut_plot_normalize_per_segment(self, dim=0, min=False) :
        """ Apply :func: `normalize_per_segment 
        <arpys.postprocessing.normalize_per_segment>` to the data in the 
        cut_plot and visualize the result. 

        :Note:
        This result is not stored, does not affect other plots (like cut_plot 
        and the x- and y-plots) and is lost the next time the cut_plot is 
        updated by any means.
        To create a more persisting result, see :func: `normalize_per_segment 
        <ds_arpes_plugin.ARPES_Plugin.normalize_per_segment>`
        """
        data = self.main_window.cut_plot.image_data
        norm_data = pp.normalize_per_segment(data, dim=dim)
        self.main_window.cut_plot.set_image(norm_data, 
                                            lut=self.main_window.lut) 

    def normalize_per_segment(self, dim=0, min=False) :
        """ Apply :func: `normalize_per_segment 
        <arpys.postprocessing.normalize_per_segment>` to every slice along z.

        :Note:
        The result of this operation is stored, i.e. the dataset is updated.
        If you just want to have a quick look at what this operation might 
        look like without applying it to the whole dataset, confer :func:
        `main_plot_normalize_per_segment 
        <ds_arpes_plugin.ARPES_Plugin.main_plot_normalize_per_segment>` or
        :func: `cut_plot_normalize_per_segment 
        <ds_arpes_plugin.ARPES_Plugin.cut_plot_normalize_per_segment>`
        """
        data = self.data_handler.get_data()
        for z in data.shape[-1] :
            pp.normalize_per_segment(data[:,:,z], dim=dim)
        self.data_handler.set_data(data)

