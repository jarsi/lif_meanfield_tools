LIF Mean-field Tools
====================
This python package provides useful tools for analyzing neuronal networks
consisting of leaky integrate and fire (LIF) neurons. These tools are based on
mean-field theory of neuronal networks. That is why this package is called
lif_meanfield_tools (LMT).

Using this package, you can easily calculate quantities like firing rates, power
spectra, and many more, which give you a deeper and more intuitive understanding
of what your network does. If your network is not behaving the way you want it
to, these tools might help you to figure out, or even tell you, what you need to
change in order to achieve the desired behaviour.

We are always trying to improve and simplify the usage of this package.
Therefore, it is easy to store (and in the future, to plot) your results and
reuse them for further analyses. We are always happy about feedback. So please
do not hesitate to contact us, if you think that we could improve your life (or
workflow).

# Structure

<img src="https://github.com/INM-6/lif_meanfield_tools/blob/master/readme_figures/structure_new.png" width="400">        

lif_meanfield_tools consists of four modules:

- The central module is **network.py**. It defines a class 'Network' which is a
  container for network parameters, analysis parameters and calculated results.
  Network comes with all the methods that can be used to calculate network
  properties, like for example firing rates or power spectra. Additionally,
  there are some 'administrative' methods for changing parameters or saving.

- **input_output.py** is called by network.py for everything that is related to
  input or output. Here we defined saving and loading routines, quantity format
  conversions and hash creation.

- **meanfield_calcs.py** is the module which is called every time a mean-field
  related method of Network is called. Here we put all the mathematical details
  of the mean-field theory.

- **aux_calcs.py** is a module where auxiliary calculations that are needed in
  meanfield_calcs.py are defined. It is difficult to draw a line between the
  calculations that belong to meanfield_calcs and the ones that belong to
  aux_calcs. We mainly introduced this module to be able to keep as much of the
  former code's structure as possible.

# How to get started / Installation

Install lif_meanfield_tools:
```
pip install git+https://github.com/INM-6/lif_meanfield_tools.git
```

# How to use this package

In order to give you a quick and simple start, we wrote a little example script:
`example/minimal_usage_example.py`. First of all, you should have a look at this
file. Actually, we hope that the usage might be self-explanatory, once you have
seen an example. But, if you need a little more hints, just continue reading.

For using LMT, you need to store all your network parameters and your analysis
parameters in yaml files, as we have done it for the example script. If you
don't know how the yaml file format works, you could either first read something
about it, or use our example yaml files as templates.

So, let us start coding. First of all you need to import the package itself.
Additionally, you might want to define a variable to store the pint unit
registry (ureg). This is needed for dealing with units and some of the
functionality implemented needs the usage of pint units.

Now, you can instantiate a network by calling the central LMT class 'Network'
and passing the yaml file names. A Network object represents your network. When
it is instantiated, it first calculates all the parameters that are derived from
the passed parameters. Then, it stores all the parameters associated with the
network under consideration. Additionally, it checks whether these parameters
have been used for an analysis before, and if so loads the corresponding
results. Newly calculated results are stored withing the Network object as well.

A Network object has the ability to tell you about it's properties, simply by
calling the corresponding method as
```
	network.property()
```
Here, `property` can be replaced by lots of stuff, like for example
`firing_rates`, `transfer_function`, or `power_spectra`. You can find the
complete list of Network methods at the end of this chapter. When such a method
is called, the network first checks whether this quantity has been calculated
before. If so, it returns the stored value. If not, it does the calculations,
stores the results, and returns them.

Sometimes, you might want to know a property for some specific parameter, like
for example the `power_spectra` at a certain frequency. Then, you need to pass
the parameter including its unit to the method, e.g.
```
	network.property(10 * ureg.Hz)
```
If you want to save your results, you can simply call
```
	network.save()
```
and the calculated results, together with the corresponding parameters, will be
stored inside a h5 file, whose name contains a hash, which reflects the used
network parameters.

Network methods:
- __save__: Save all calculated results together with network and analysis
  parameters into an h5 file.
- __show__: Return a list of quantities that have already been calculated.
- __change_parameters__: Create a new instance of Network class with adjusted
  specified parameters.
- __firing_rates__: Calculate the firing rates in a self-consistent mean-field
  manner. The algorithm starts with firing rate zero for all populations, then
  calculates the resulting mean and variance of the input to a neuron, and uses
  the results and equation (4.33) in Fourcaud & Brunel 2002 to calculate the
  resulting firing rate again. This procedure is continued until the rates
  converge.
- __mean_input__: Calculate mean input to a neuron, given the population firing
  rates and external inputs.
- __std_input__: Calculate the standard deviation of the input to a neuron,
  given the population firing rates and external inputs.
- __working_point__: Return firing rate, mean and standard deviation of input.
- __delay_dist_matrix__: ???
- __transfer_function__: Calculate the transfer function following equation (93)
  in Schuecker et al. 2014 in first order perturbation theory in $
  \sqrt(tau_s/tau_m) $, the square root of the synaptic time constant divided by
  the membrane time constant. Note that the results are not accurate in the high
  frequency limit.
- __sensitivity_measure__: Calculate the sensitivity measure, introduced in Bos
  et al. 2016, equation (7), which can be used to identify the connections
	crucial for the peak amplitude and frequency of network oscillations, visible
	in the power spectrum.
- __power_spectra__: Calculate the power spectra of all populations following
  equation (18) in Bos 2016.
- __eigen_spectra__: Calculate the eigenvalue spectrum, or left of right
  eigenvectors of the effective connectivity matrix (eq. 4), the propagator
	(eq. 16) or the inverse propagator in the frequency	domain as defined in Bos
	et al. 2016.


# History of this Project

Mean-field theory is a very handy tool when you want to understand the behaviour
of your network. Using this theory allows you to predict some features of a
network without running a single (often very time consuming) simulation.

At our institute, the INM-6 at the Research Center Juelich, we, among other
things, investigate and develop such mean-field tools. Over the years, more and
more of the tools, developed by ourselves and other researchers, have been
implemented. In particular, the primary work for this package has been done by
Hannah Bos, Jannis Schuecker and Moritz Helias. Here we extend the work
published in the repository [https://github.com/INM-6/neural_network_meanfield]
and make it available to a wider audience.  

Our aim was to make use the convenient tools that were kind of concealed by the
complexity of the code as it was at that time. Hence, we decided to restructure
and rewrite the code in such a way that people could use it without
understanding the underlying theory. We changed a lot of things. We simplified
the code. We introduced units and decided to store the parameters in separate
yaml files. We wanted the users to only have to interact with one module. So, we
collected all the functionality in the network.py module. We ported the code to
python 3. We made the whole thing a package. We expanded the documentation a
lot. We simplified saving results together with the parameters. And so on.

What we ended up with is the package that you are currently interested in. It
contains several tools for analyzing neuronal networks. And it is very simple to
use.
