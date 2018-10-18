"""
network.py: Main class providing functions to calculate the stationary and
dynamical properties of a given circuit.

Authors: Hannah Bos, Jannis Schuecker
"""
from __future__ import print_function
import numpy as np
import functools
from decorator import decorator

# import lif_meanfield_tools.input_output as io
from . import input_output as io
from . import meanfield_calcs
from .__init__ import ureg

class Network(object):
    """
    Network with given parameters. The class provides methods for calculating
    stationary and dynamical properties of the defined network.

    Parameters:
    -----------
    network_params: str
        specifies path to yaml file containing network parameters
    analysis_params: str
        specifies path to yaml file containing analysis parameters
    new_network_params: dict
        dictionary specifying network parameters from yaml file that should be
        overwritten. Format:
        {'<param1>:{'val':<value1>, 'unit':<unit1>},...}
    new_analysis_params: dict
        dictionary specifying analysis parameters from yaml file that should be
        overwritten. Format:
        {'<param1>:{'val':<value1>, 'unit':<unit1>},...}
    """

    def __init__(self, network_params, analysis_params, new_network_params={},
                 new_analysis_params={}):
        """
        Initiate Network class.

        Load parameters from given yaml files using input output handling
        implemented in io.py and store them as instance variables.
        Overwrite parameters specified in new_network_parms and
        new_analysis_params.
        Calculate parameters which are derived from given parameters.
        Try to load existing results.
        """

        # store yaml file names
        self.network_params_yaml = network_params
        self.analysis_params_yaml = analysis_params

        # load network params (read from yaml and convert to quantities)
        self.network_params = io.load_params(network_params)
        # load analysis params (read from yaml and convert to quantities)
        self.analysis_params = io.load_params(analysis_params)

        # # convert new params to quantities
        # new_network_params_converted = io.val_unit_to_quantities(
        #                                                     new_network_params)
        # new_analysis_params_converted = io.val_unit_to_quantities(
        #                                                     new_analysis_params)
        # update network parameters
        self.network_params.update(new_network_params)
        # update analysis parameters
        self.analysis_params.update(new_analysis_params)

        # calculate dependend network parameters
        derived_network_params = self._calculate_dependent_network_parameters()
        self.network_params.update(derived_network_params)

        # calculate dependend analysis parameters
        derived_analysis_params = self._calculate_dependent_analysis_parameters()
        self.analysis_params.update(derived_analysis_params)
        # load already existing results
        stored_analysis_params, self.results = io.load_from_h5(self.network_params)
        self.analysis_params.update(stored_analysis_params)


    def _calculate_dependent_network_parameters(self):
        """
        Calculate all network parameters derived from parameters in yaml file

        Returns:
        --------
        dict
            dictionary containing all derived network parameters
        """

        derived_params = {}

        if self.network_params['label'] == 'microcircuit':

            # convert weights in pA to weights in mV
            derived_params['j'] = (self.network_params['tau_s']
                                  * self.network_params['w']
                                  / self.network_params['C']).to(ureg.mV)

            # reset reference potential to 0
            derived_params['V_0_rel'] = 0 * ureg.mV
            derived_params['V_th_rel'] = (self.network_params['V_th_abs']
                                     - self.network_params['V_0_abs'])

            # standard deviation of delay of excitatory connections
            derived_params['d_e_sd'] = self.network_params['d_e']*0.5
            # standard deviation of delay of inhibitory connections
            derived_params['d_i_sd'] = self.network_params['d_i']*0.5

            # weight matrix
            J = np.ones((8,8))*derived_params['j']
            J[1:8:2] *= -self.network_params['g']
            J = np.transpose(J)
            # larger weight for L4E->L23E connections
            J[0][2] *= 2.0
            derived_params['J'] = J

            # delay matrix
            D = np.ones((8,8))*self.network_params['d_e']
            D[1:8:2] = np.ones(8)*self.network_params['d_i']
            D = np.transpose(D)
            derived_params['Delay'] = D

            # delay standard deviation matrix
            D = np.ones((8,8))*derived_params['d_e_sd']
            D[1:8:2] = np.ones(8)*derived_params['d_i_sd']
            D = np.transpose(D)
            derived_params['Delay_sd'] = D

            # calculate dimension of system
            derived_params['dimension'] = len(self.network_params['populations'])

        return derived_params


    def _calculate_dependent_analysis_parameters(self):
        """
        Calculate all analysis parameters derived from parameters in yaml file

        Returns:
        --------
        dict
            dictionary containing derived parameters
        """

        derived_params = {}

        # convert regular to angular frequencies
        w_min = 2*np.pi*self.analysis_params['f_min']
        w_max = 2*np.pi*self.analysis_params['f_max']
        dw = 2*np.pi*self.analysis_params['df']

        # enable usage of quantities
        @ureg.wraps(ureg.Hz, (ureg.Hz, ureg.Hz, ureg.Hz))
        def calc_evaluated_omegas(w_min, w_max, dw):
            """ Calculates omegas at which functions are to be evaluated """
            return np.arange(w_min, w_max, dw)

        derived_params['omegas'] = calc_evaluated_omegas(w_min, w_max, dw)

        return derived_params


    def _check_and_store(result_key, analysis_key=''):
        """
        Decorator function that checks whether result are already existing.

        This decorator serves as a wrapper for functions that calculate
        quantities which are to be stored in self.results. First it checks,
        whether the result already has been stored in self.results. If this is
        the case, it returns that result. If not, the calculation is executed,
        the result is stored in self.results and the result is returned.

        If the wrapped function gets additional parameters passed, one should
        also include an analysis key, under which the new analysis parameters
        should be stored in the dictionary self.analysis_params. Then, the
        decorator first checks, whether the given parameters have been used
        before and returns the corresponding results.

        Parameters:
        -----------
        result_key: str
            Specifies under which key the result should be stored.
        analysis_key: str
            Specifies under which key the analysis_parameter should be stored.

        Returns:
        --------
        func
            decorator function
        """
        @decorator
        def decorator_check_and_store(func, self, *args, **kwargs):
            """ Decorator with given parameters, returns expected results. """
            # collect analysis_params
            analysis_params = getattr(self, 'analysis_params')
            # collect results
            results = getattr(self, 'results')

            if analysis_key:
                # collect input
                analysis_param = args[0]
                # are analysis_keys and analysis_params already existing?
                if analysis_key in analysis_params.keys():
                    if analysis_param in analysis_params[analysis_key]:
                        # get index of analysis_key
                        index = list(analysis_params[analysis_key]).index(analysis_param)
                        # return corresponding result
                        return results[result_key][index]
                    else:
                        # store analysis_param in corresponding list
                        if isinstance(analysis_param, ureg.Quantity):
                            analysis_params[analysis_key] = (np.append(analysis_params[analysis_key].magnitude,
                                                                       analysis_param.magnitude)
                                                             * analysis_param.units)
                        else:
                            analysis_params[analysis_key] = (np.append(analysis_params[analysis_key],
                                                                       analysis_param))

                        setattr(self, 'analysis_params', analysis_params)
                        # calculate new results
                        new_result = func(self, *args, **kwargs)
                        # save new results
                        results[result_key] = list(results[result_key])
                        results[result_key].append(new_result)
                        setattr(self, 'results', results)
                        # return new result
                        return new_result

                else:
                    # store analysis_params
                    if isinstance(analysis_param, ureg.Quantity):
                        analysis_params[analysis_key] = (np.array([analysis_param.magnitude])
                                                         * analysis_param.units)
                    else:
                        analysis_params[analysis_key] = np.array([analysis_param])
                    setattr(self, 'analysis_params', analysis_params)
                    # calculate new results
                    new_result = func(self, *args, **kwargs)
                    results[result_key] = [new_result]
                    # save new results
                    setattr(self, 'results', results)
                    # return new result
                    return new_result

            else:
                # check if new result is already stored in self.results
                if result_key in results.keys():
                    # if so, return already calcualted result
                    return results[result_key]
                else:
                    # if not, calculate new result
                    results[result_key] = func(self, *args, **kwargs)
                    # update self.results
                    setattr(self, 'results', results)
                    # return new_result
                    return results[result_key]

            # return wrapper_check_and_store
        return decorator_check_and_store


    def save(self, param_keys={}, output_name=''):
        """
        Saves results and parameters to h5 file

        Parameters:
        -----------
        param_keys: dict
            specifies which parameters are used in hash for output name
        output_name: str
            if given, this is used as output file name

        Returns:
        --------
        None
        """

        io.save(self.results, self.network_params, self.analysis_params,
                param_keys, output_name)


    def show(self):
        """ Returns which results have already been calculated """
        return sorted(list(self.results.keys()))


    def change_parameters(self, changed_network_params={},
                          changed_analysis_params={}):
        """
        Change parameters and return new network with specified parameters.

        Parameters:
        -----------
        new_network_parameters: dict
            Dictionary specifying which parameters should be altered.

        Returns:
        Network object
            New network with specified parameters.
        """

        new_network_params = self.network_params
        new_network_params.update(changed_network_params)
        new_analysis_params = self.analysis_params
        new_analysis_params.update(changed_analysis_params)

        return Network(self.network_params_yaml, self.analysis_params_yaml,
                       new_network_params, new_analysis_params)


    @_check_and_store('firing_rates')
    def firing_rates(self):
        """ Calculates firing rates """
        return meanfield_calcs.firing_rates(self.network_params['dimension'],
                                            self.network_params['tau_m'],
                                            self.network_params['tau_s'],
                                            self.network_params['tau_r'],
                                            self.network_params['V_0_rel'],
                                            self.network_params['V_th_rel'],
                                            self.network_params['K'],
                                            self.network_params['J'],
                                            self.network_params['j'],
                                            self.network_params['nu_ext'],
                                            self.network_params['K_ext'])


    @_check_and_store('mu')
    def mean(self):
        """ Calculates mean """
        return meanfield_calcs.mean(self.firing_rates(),
                                    self.network_params['K'],
                                    self.network_params['J'],
                                    self.network_params['j'],
                                    self.network_params['tau_m'],
                                    self.network_params['nu_ext'],
                                    self.network_params['K_ext'])

    @_check_and_store('sigma')
    def standard_deviation(self):
        """ Calculates variance """
        return meanfield_calcs.standard_deviation(self.firing_rates(),
                                                  self.network_params['K'],
                                                  self.network_params['J'],
                                                  self.network_params['j'],
                                                  self.network_params['tau_m'],
                                                  self.network_params['nu_ext'],
                                                  self.network_params['K_ext'])


    def working_point(self):
        """
        Calculates stationary working point of the network.

        Returns:
        --------
        dict
            dictionary specifying mean, variance and firing rates
        """

        # first define functions that keep track of already existing results

        # then do calculations
        working_point = {}
        working_point['firing_rates'] = self.firing_rates()
        working_point['mu'] = self.mean()
        working_point['sigma'] = self.standard_deviation()

        return working_point



    def delay_dist_matrix(self, freq=None):
        """
        Calculates delay dist matrix either for all frequencies or given one.

        Paramters:
        ----------
        freq: Quantity(float, 'Hertz')
            Optional paramter. If given, delay dist matrix is only calculated
            for this frequency.

        Returns:
        --------
        Quantity(np.ndarray, 'Hz/mV')
            Delay dist matrix, either as an array with shape(dimension,
            dimension) for a given frequency, or shape(dimension, dimension,
            len(omegas)) for no specified frequency.
        """

        if freq == None:
            return self.delay_dist_matrix_multi()
        else:
            return self.delay_dist_matrix_single(freq)


    @_check_and_store('delay_dist')
    def delay_dist_matrix_multi(self):
        """
        Calculates delay distribution matrix for all omegas.

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless'):
            Delay distribution matrix.
        """

        return meanfield_calcs.delay_dist_matrix(self.network_params['dimension'],
                                                 self.network_params['Delay'],
                                                 self.network_params['Delay_sd'],
                                                 self.network_params['delay_dist'],
                                                 self.analysis_params['omegas'])

    @_check_and_store('delay_dist_single', 'delay_dist_freqs')
    def delay_dist_matrix_single(self, omega):
        """
        Calculates delay distribution matrix for one omega.

        Parameters:
        -----------
        omega: Quantity(float, 'Hertz')
            Frequency for which delay distribution matrix should be calculated.
        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless'):
            Delay distribution matrix.
        """

        return meanfield_calcs.delay_dist_matrix(self.network_params['dimension'],
                                                 self.network_params['Delay'],
                                                 self.network_params['Delay_sd'],
                                                 self.network_params['delay_dist'],
                                                 [omega])[0]



    def transfer_function(self, freq=None):
        """
        Calculates transfer function either for all frequencies or given one.

        Paramters:
        ----------
        freq: Quantity(float, 'Hertz')
            Optional paramter. If given, transfer function is only calculated
            for this frequency.

        Returns:
        --------
        Quantity(np.ndarray, 'Hz/mV')
            Transfer function, either as an array with shape(dimension,) for a
            given frequency, or shape(dimension, len(omegas)) for no specified
            frequency.
        """

        if freq == None:
            return self.transfer_function_multi()
        else:
            return self.transfer_function_single(freq)


    @_check_and_store('transfer_function')
    def transfer_function_multi(self):
        """
        Calculates transfer function for each population.

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless'):
            Transfer functions for all populations evaluated at specified
            omegas.
        """

        transfer_functions = meanfield_calcs.transfer_function(self.mean(),
                                                 self.standard_deviation(),
                                                 self.network_params['tau_m'],
                                                 self.network_params['tau_s'],
                                                 self.network_params['tau_r'],
                                                 self.network_params['V_th_rel'],
                                                 self.network_params['V_0_rel'],
                                                 self.network_params['dimension'],
                                                 self.analysis_params['omegas'])

        return transfer_functions



    @_check_and_store('transfer_function_single', 'transfer_freqs')
    def transfer_function_single(self, freq):
        """
        Calculates transfer function for each population.

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless'):
            Transfer functions for all populations evaluated at specified
            omegas.
        """

        omega = freq * 2 * np.pi

        transfer_functions = meanfield_calcs.transfer_function(self.mean(),
                                                 self.standard_deviation(),
                                                 self.network_params['tau_m'],
                                                 self.network_params['tau_s'],
                                                 self.network_params['tau_r'],
                                                 self.network_params['V_th_rel'],
                                                 self.network_params['V_0_rel'],
                                                 self.network_params['dimension'],
                                                 [omega])

        return transfer_functions


    @_check_and_store('sensitivity_measure', 'sensitivity_freqs')
    def sensitivity_measure(self, freq):
        """
        Calculates the sensitivity measure for the given frequency.

        Following Eq. 21 in Bos et al. (2015).

        Parameters:
        -----------
        freq: Quantity(float, 'hertz')
            Regular frequency at which sensitivity measure is evaluated.

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless')
            Sensitivity measure.
        """

        # convert regular frequency to angular frequeny
        omega = freq * 2 * np.pi

        # calculate needed transfer_function
        transfer_function = meanfield_calcs.transfer_function(self.mean(),
                                                 self.standard_deviation(),
                                                 self.network_params['tau_m'],
                                                 self.network_params['tau_s'],
                                                 self.network_params['tau_r'],
                                                 self.network_params['V_th_rel'],
                                                 self.network_params['V_0_rel'],
                                                 self.network_params['dimension'],
                                                 [omega])
        if omega.magnitude < 0:
            transfer_function = np.conjugate(transfer_function)

        # calculate needed delay distribution matrix
        delay_dist_matrix = meanfield_calcs.delay_dist_matrix(self.network_params['dimension'],
                                                              self.network_params['Delay'],
                                                              self.network_params['Delay_sd'],
                                                              self.network_params['delay_dist'],
                                                              omega)

        return meanfield_calcs.sensitivity_measure(transfer_function,
                                                   delay_dist_matrix,
                                                   self.network_params['J'],
                                                   self.network_params['tau_m'],
                                                   self.network_params['tau_s'],
                                                   self.network_params['dimension'],
                                                   omega)


    @_check_and_store('power_spectra')
    def power_spectra(self):
        """
        Calculates power spectra.
        """

        return meanfield_calcs.power_spectra(self.network_params['tau_m'],
                                             self.network_params['tau_s'],
                                             self.network_params['dimension'],
                                             self.network_params['J'],
                                             self.network_params['K'],
                                             self.delay_dist_matrix(),
                                             self.network_params['N'],
                                             self.firing_rates(),
                                             self.transfer_function(),
                                             self.analysis_params['omegas'])



    @_check_and_store('eigenvalue_spectra', 'eigenvalue_matrix')
    def eigenvalue_spectra(self, matrix):
        """
        Calculates the eigenvalues of the specified matrix at given frequency.

        Paramters:
        ----------
        matrix: str
            Specifying matrix which is analysed. Options are the effective
            connectivity matrix ('MH'), the propagator ('prop') and
            the inverse of the propagator ('prop_inv').

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless')
            Eigenvalues.
        """

        return  meanfield_calcs.eigen_spectra(self.network_params['tau_m'],
                                                   self.network_params['tau_s'],
                                                   self.transfer_function(),
                                                   self.network_params['dimension'],
                                                   self.delay_dist_matrix(),
                                                   self.network_params['J'],
                                                   self.analysis_params['omegas'],
                                                   'eigvals',
                                                   matrix)

    @_check_and_store('r_eigenvec_spectra', 'r_eigenvec_matrix')
    def r_eigenvec_spectra(self, matrix):
        """
        Calculates the right eigenvecs of the specified matrix at given freq.

        Paramters:
        ----------
        matrix: str
            Specifying matrix which is analysed. Options are the effective
            connectivity matrix ('MH'), the propagator ('prop') and
            the inverse of the propagator ('prop_inv').

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless')
            Right eigenvectors.
        """
        return  meanfield_calcs.eigen_spectra(self.network_params['tau_m'],
                                                   self.network_params['tau_s'],
                                                   self.transfer_function(),
                                                   self.network_params['dimension'],
                                                   self.delay_dist_matrix(),
                                                   self.network_params['J'],
                                                   self.analysis_params['omegas'],
                                                   'reigvecs',
                                                   matrix)



    @_check_and_store('l_eigenvec_spectra', 'l_eigenvec_matrix')
    def l_eigenvec_spectra(self, matrix):
        """
        Calculates the left eigenvecs of the specified matrix at given freq.

        Paramters:
        ----------
        matrix: str
            Specifying matrix which is analysed. Options are the effective
            connectivity matrix ('MH'), the propagator ('prop') and
            the inverse of the propagator ('prop_inv').

        Returns:
        --------
        Quantity(np.ndarray, 'dimensionless')
            Left eigenvectors.
        """
        return  meanfield_calcs.eigen_spectra(self.network_params['tau_m'],
                                                   self.network_params['tau_s'],
                                                   self.transfer_function(),
                                                   self.network_params['dimension'],
                                                   self.delay_dist_matrix(),
                                                   self.network_params['J'],
                                                   self.analysis_params['omegas'],
                                                   'leigvecs',
                                                   matrix)



"""circuit.py: Main class providing functions to calculate the stationary
and dynamical properties of a given circuit.

Authors: Hannah Bos, Jannis Schuecker
"""

# import numpy as np
# from setup import Setup
# from analytics import Analytics


class Circuit(object):
    """Provides functions to calculate the stationary and dynamical
    properties of a given circuit.

    Arguments:
    label: string specifying circuit, options: 'microcircuit'

    Keyword Arguments:
    params: dictionary specifying parameter of the circuit, default
            parameter given in params_circuit.py will be overwritten
    analysis_type: string specifying level of analysis that is requested
                   default: 'dynamical'
                   options:
                   - None: only circuit and default analysis parameter
                     are set
                   - 'stationary': circuit and default analysis parameter
                      are set, mean and variance of input to each
                      populations as well as firing rates are calculated
                   - 'dynamical': circuit and default analysis parameter
                      are set, mean and variance of input to each
                      populations as well as firing rates are calculated,
                      variables for calculation of spectra are calculated
                      including the transfer function for all populations
    fmin: minimal frequency in Hz, default: 0.1 Hz
    fmax: maximal frequency in Hz, default: 150 Hz
    df: frequency spacing in Hz, default: 1.0/(2*np.pi) Hz
    to_file: boolean specifying whether firing rates and transfer
             functions are written to file, default: True
    from_file: boolean specifying whether firing rates and transfer
               functions are read from file, default: True
               if set to True and file is not found firing rates and
               transfer function are calculated
    """
    def __init__(self, label, params={}, **kwargs):
        """Initiates circuit class:
        Instantiates Setup and Analysis,
        checks analysis type,
        saves default for (arbitrary) analysis parameters (like minimum and maximum frequency
        considered, or increment size) as attributes,
        calculates and saves parameters that need to be calculated from analysis parameters,
        calculates and saves parameters that need to be calculated using analysis.py (but thereto
        uses instance of setup)"""
        # specifies circuit, e.g. 'microcircuit'
        self.label = label
        # instantiated Classes Setup and Analysis
        self.setup = Setup()
        self.ana = Analytics()
        # check analysis type, default is 'dynamical'
        if 'analysis_type' in kwargs:
            self.analysis_type = kwargs['analysis_type']
        else:
            self.analysis_type = 'dynamical'
        # set default analysis and circuit parameter
        self._set_up_circuit(params, kwargs)
        # set parameter derived from analysis and circuit parameter
        new_vars = self.setup.get_params_for_analysis(self)
        new_vars['label'] = self.label
        self._set_class_variables(new_vars)
        # set variables which require calculation in analytics class
        self._calc_variables()

    # updates variables of Circuit() and Analysis() classes, new variables
    # are specified in the dictionary new_vars
    def _set_class_variables(self, new_vars):
        """saves given new_vars as attributes of network class instance
        AND as attributes of the instance variable self.ana, which is an istance
        of the class Analytics itself. (two seperate places where variables are stored!)"""
        for key, value in new_vars.items():
            setattr(self, key, value)
        if 'params' in new_vars:
            for key, value in new_vars['params'].items():
                setattr(self, key, value)
        self.ana.update_variables(new_vars)

    # updates class variables of variables of Circuit() and Analysis()
    # such that default analysis and circuit parameters are known
    def _set_up_circuit(self, params, args):
        """gets default analysis parameters from setup.py (stored there)
        and circuit parameters stored in params_circuit.py are collected using setup.py
        and a hash is created via params_circuit.py and stored as Network instance variable"""
        # set default analysis parameter
        new_vars = self.setup.get_default_params(args)
        self._set_class_variables(new_vars)
        # set circuit parameter
        new_vars = self.setup.get_circuit_params(self, params)
        self._set_class_variables(new_vars)

    # quantities required for stationary analysis are calculated
    def _set_up_for_stationary_analysis(self):
        """calculates and saves working point values using setup.py, which itself
        uses the instance of Analytics to calculate these values. """
        new_vars = self.setup.get_working_point(self)
        self._set_class_variables(new_vars)

    # quantities required for dynamical analysis are calculated
    def _set_up_for_dynamical_analysis(self):
        """ calculates and saves the variables needed for the calculation of spectra
        using setup.py, which itself uses the instance of Analytics to calculate these
        valuse."""
        new_vars = self.setup.get_params_for_power_spectrum(self)
        self._set_class_variables(new_vars)

    # calculates quantities needed for analysis specified by analysis_type
    def _calc_variables(self):
        """calculates the quantities needed for analysis using the functions
        given above and ensures, that nothing unnecessary is calculated."""
        if self.analysis_type == 'dynamical':
            self._set_up_for_stationary_analysis()
            self._set_up_for_dynamical_analysis()
        elif self.analysis_type == 'stationary':
            self._set_up_for_stationary_analysis()

    def alter_params(self, params):
        """Parameter specified in dictionary params are changed.
        Changeable parameters are default analysis and circuit parameter,
        as well as label and analysis_type.

        Arguments:
        params: dictionary, specifying new parameters
        """
        self.params.update(params)
        # calculate and change new parameters for circuit
        new_vars = self.setup.get_altered_circuit_params(self, self.label)
        self._set_class_variables(new_vars)
        # use new circuit to calculate and save analysis parameters
        new_vars = self.setup.get_params_for_analysis(self)
        self._set_class_variables(new_vars)
        # calculate needed quantities again
        self._calc_variables()

#################################################################################################
    """ Here the part with the functional methods beginns"""

    def create_power_spectra(self):
        """Returns frequencies and power spectra.
        See: Eq. 9 in Bos et al. (2015)
        Shape of output: (len(self.populations), len(self.omegas))

        Output:
        freqs: vector of frequencies in Hz
        power: power spectra for all populations,
               dimension len(self.populations) x len(freqs)
        """
        power = np.asarray(list(map(self.ana.spec, self.ana.omegas)))
        return self.ana.omegas/(2.0*np.pi), np.transpose(power)

    def create_power_spectra_approx(self):
        """Returns frequencies and power spectra approximated by
        dominant eigenmode.
        See: Eq. 15 in Bos et al. (2015)
        Shape of output: (len(self.populations), len(self.omegas))

        Output:
        freqs: vector of frequencies in Hz
        power: power spectra for all populations,
               dimension len(self.populations) x len(freqs)
        """
        power = np.asarray(list(map(self.ana.spec_approx, self.ana.omegas)))
        return self.ana.omegas/(2.0*np.pi), np.transpose(power)

    def create_eigenvalue_spectra(self, matrix):
        """Returns frequencies and frequency dependence of eigenvalues of
        matrix.

        Arguments:
        matrix: string specifying the matrix, options are the effective
                connectivity matrix ('MH'), the propagator ('prop') and
                the inverse of the propagator ('prop_inv')

        Output:
        freqs: vector of frequencies in Hz
        eigs: spectra of all eigenvalues,
              dimension len(self.populations) x len(freqs)
        """
        eigs = [self.ana.eigs_evecs(matrix, w)[0] for w in self.ana.omegas]
        eigs = np.transpose(np.asarray(eigs))
        return self.ana.omegas/(2.0*np.pi), eigs

    def create_eigenvector_spectra(self, matrix, label):
        """Returns frequencies and frequency dependence of
        eigenvectors of matrix.

        Arguments:
        matrix: string specifying the matrix, options are the effective
                connectivity matrix ('MH'), the propagator ('prop') and
                the inverse of the propagator ('prop_inv')
        label: string specifying whether spectra of left or right
               eigenvectors are returned, options: 'left', 'right'

        Output:
        freqs: vector of frequencies in Hz
        evecs: spectra of all eigenvectors,
               dimension len(self.populations) x len(freqs) x len(self.populations)
        """
        # one list entry for every eigenvector, evecs[i][j][k] is the
        # ith eigenvectors at the jth frequency for the kth component
        evecs = [np.zeros((len(self.ana.omegas), self.ana.dimension),
                          dtype=complex) for i in range(self.ana.dimension)]
        for i, w in enumerate(self.ana.omegas):
            eig, vr, vl = self.ana.eigs_evecs(matrix, w)
            if label == 'right':
                v = vr
            elif label == 'left':
                v = vl
            for j in range(self.ana.dimension):
                evecs[j][i] = v[j]
        evecs = np.asarray([np.transpose(evecs[i]) for i in range(self.ana.dimension)])
        return self.ana.omegas/(2.0*np.pi), evecs

    def reduce_connectivity(self, M_red):
        """Connectivity (indegree matrix) is reduced, while the working
        point is held constant.

        Arguments:
        M_red: matrix, with each element specifying how the corresponding
               connection is altered, e.g the in-degree from population
               j to population i is reduced by 30% with M_red[i][j]=0.7
        """
        M_original = self.M_full[:]
        if M_red.shape != M_original.shape:
            raise RuntimeError('Dimension of mask matrix has to be the '
                               + 'same as the original indegree matrix.')
        self.M = M_original*M_red
        self.ana.update_variables({'M': self.M})

    def restore_full_connectivity(self):
        '''Restore connectivity to full connectivity.'''
        self.M = self.M_full
        self.ana.update_variables({'M': self.M})

    def get_effective_connectivity(self, freq):
        """Returns effective connectivity matrix.

        Arguments:
        freq: frequency in Hz
        """
        return self.ana.create_MH(2*np.pi*freq)

    def get_sensitivity_measure(self, freq, index=None):
        """Returns sensitivity measure.
        see: Eq. 21 in Bos et al. (2015)

        Arguments:
        freq: frequency in Hz

        Keyword arguments:
        index: specifies index of eigenmode, default: None
               if set to None the dominant eigenmode is assumed
        """
        MH  = self.get_effective_connectivity(freq)
        e, U = np.linalg.eig(MH)
        U_inv = np.linalg.inv(U)
        if index is None:
            # find eigenvalue closest to one
            index = np.argmin(np.abs(e-1))
        T = np.outer(U_inv[index],U[:,index])
        T /= np.dot(U_inv[index],U[:,index])
        T *= MH
        return T

    def get_transfer_function(self):
        """Returns dynamical transfer function depending on frequency.
        Shape of output: (len(self.populations), len(self.omegas))

        Output:
        freqs: vector of frequencies in Hz
        dyn_trans_func: power spectra for all populations,
                        dimension len(self.populations) x len(freqs)
        """
        dyn_trans_func = np.asarray(list(map(self.ana.create_H, self.ana.omegas)))
        return self.ana.omegas/(2.0*np.pi), np.transpose(dyn_trans_func)
