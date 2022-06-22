Glue OpenSpace plugin
====================================

An experimental plugin was developed as part of the *Astrographics: Interactive Data-Driven Journeys through Space* workshop at Dagstuhl. This repository is forked from the repository https://github.com/aniisabihi/glue-openspace-thesis, which in turn is forked from the original repository at https://github.com/glue-viz/glue-openspace,

**2020**: Two master thesis students for OpenSpace, Aniisa Bihi & Johanna Granström, developed SIMP, a custom message protocol for OpenSpace. This plugin was developed further at the same time so that the messaging protocol could be tested.

**2022**: Two master thesis students for OpenSpace, Jacob Molin & Victor Lindquist, have revamped and generalized SIMP to version `1.9.1`. In this work, this plugin has also been revamped and new functionality have been added.

> **WARNING** The changes to comply with SIMP version `1.9.1` are breaking.

To try it out the 2022 verison (work in progress)::

    pip install git+https://github.com/openspace/glue-openspace.git

    Requires that the developer's version of OpenSpace is installed from the branch called 'thesis/2022/software-integration'
    Guide: http://wiki.openspaceproject.com/
    Branch: https://github.com/OpenSpace/OpenSpace/tree/thesis/2022/software-integration

To try it out the 2020 verison::

    pip install git+https://github.com/aniisabihi/glue-openspace-thesis.git

    Requires that the developer's version of OpenSpace is installed from the branch called 'thesis/2020/software-integration'
    Guide: http://wiki.openspaceproject.com/
    Branch: https://github.com/OpenSpace/OpenSpace/tree/thesis/2020/software-integration
