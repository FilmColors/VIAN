==============
Color Concepts
==============

In this section, you find an overview over the concepts, that are being used in
VIAN, and what you can read out of the various analyses that VIAN offers.

First of all, it is important to note that all of VIAN's visualizations of
color properties and analyses are in the CIE L*a*b*- (or, simply, Lab-) space.
Sometimes, elements or color properties of them are mapped into a sub-space of
CIE L*a*b* - e.g. in some visualizations, the average color of screenshots may
be displayed on the 2D-plane of their ab-values.

But let's first look at what the CIE L*a*b* space actually is:

CIE L*a*b*
**********

The CIE L*a*b* color space is a way to arrange colors in a intuitively
understandable way:
The three letters **L**, **a**, and **b** stand for the three parameters according to
which the colors are arranged in this color space:

- **L**: The Lightness of the color. The lighter the color, the higher is this
  value. It ranges from 0 (black) to 100 (white).
- **a**: The color on the green-red axis.
- **b**: The color on the blue-yellow axis.

Normally, the **a** and **b** values are mapped into a 2D plane, while the
**L** value is conceptualized orthogonal to this ab-plane.

.. figure:: CIE_Lab.jpg
   :scale: 60%
   :align: center
   :alt: map to buried treasure
   
   The CIE L*a*b* color space, modelled as sphere. Credits: [#]_.

An important property of the CIE L*a*b* space is that it is a so called
«perceptually uniform» representation of colors:
If we were to add a certain amount of lightness to two different colors, the
modelling in CIE L*a*b* would ensure that both resulting colors will end up in
a similar place relevant to their original ones.

Visualizations of VIAN Analyses
*******************************



For more details, see e.g. the CIE L*a*b* article in `Wikipedia
<https://en.wikipedia.org/wiki/CIELAB_color_space>`_.

Further readings:

- `Halter, Gaudenz; Ballester-Ripoll, Rafael; Flueckiger, Barbara; Pajarola, Renato (2019): VIAN. A Visual Annotation Tool for Film Analysis.  In: Computer Graphics Forum, 38,1.
  <https://onlinelibrary.wiley.com/doi/full/10.1111/cgf.13676>`_.

.. [#] Ly, Bao & Dyer, Ethan & Feig, Jessica & Chien, Anna & Bino, Sandra. (2020). Research Techniques Made Simple: Cutaneous Colorimetry: A Reliable Technique for Objective Skin Color Measurement. The Journal of investigative dermatology. 140. 3-12.e1. 10.1016/j.jid.2019.11.003.

.. toctree::
    :maxdepth: 4

