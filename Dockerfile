FROM intel4coro/jupyter-ros2:jazzy-py3.12

USER ${NB_USER}
ENV ROS_WS=/home/${NB_USER}/ros2_ws

# Set up the ROS2 workspace
RUN mkdir -p ${ROS_WS}/src
WORKDIR ${ROS_WS}/src

# Clone and install pycram.
# pycram has no package.xml, so it is not a colcon package and must be
# installed directly with pip instead of being built via colcon.
RUN git clone --depth 1 https://github.com/cram2/pycram.git
RUN git config --global --add safe.directory ${ROS_WS}/src/pycram
RUN pip install --no-cache-dir -e ${ROS_WS}/src/pycram

# iai_pr2_description contains the PR2 robot's URDF/xacro model, which
# coraplex.testing.setup_world() needs for the demo world generation. It is
# a ROS1/catkin package (uses `find_package(catkin ...)`), so colcon cannot
# build it. ROS2's package lookup (ament_index_python, used internally by
# xacro's $(find pkg) substitution) does not use the ROS1 ROS_PACKAGE_PATH
# variable; it instead looks for a package name listed under
# <prefix>/share/ament_index/resource_index/packages/ for any prefix in
# AMENT_PREFIX_PATH, and then expects the package's files under
# <prefix>/share/<package_name>/. Since only the raw description files are
# needed (not an actual catkin build), this registration is created by hand:
# an empty marker file, and a symlink from share/iai_pr2_description to the
# actual cloned package contents.
RUN mkdir -p /home/${NB_USER}/ros_descriptions/iai_pr2 \
    /home/${NB_USER}/ament_prefix/share/ament_index/resource_index/packages \
    /home/${NB_USER}/ament_prefix/share
RUN git clone --depth 1 https://github.com/code-iai/iai_pr2.git \
    /home/${NB_USER}/ros_descriptions/iai_pr2
RUN git config --global --add safe.directory /home/${NB_USER}/ros_descriptions/iai_pr2
RUN touch /home/${NB_USER}/ament_prefix/share/ament_index/resource_index/packages/iai_pr2_description
RUN ln -s /home/${NB_USER}/ros_descriptions/iai_pr2/iai_pr2_description \
    /home/${NB_USER}/ament_prefix/share/iai_pr2_description

# iai_pr2_description's meshes in turn reference the upstream, original PR2
# mesh package pr2_description (from PR2/pr2_common), which is registered
# the same way.
RUN git clone --depth 1 https://github.com/PR2/pr2_common.git \
    /home/${NB_USER}/ros_descriptions/pr2_common
RUN git config --global --add safe.directory /home/${NB_USER}/ros_descriptions/pr2_common
RUN touch /home/${NB_USER}/ament_prefix/share/ament_index/resource_index/packages/pr2_description
RUN ln -s /home/${NB_USER}/ros_descriptions/pr2_common/pr2_description \
    /home/${NB_USER}/ament_prefix/share/pr2_description

ENV AMENT_PREFIX_PATH=/home/${NB_USER}/ament_prefix:$AMENT_PREFIX_PATH

# The apartment world in coraplex/resources/worlds/apartment.urdf references
# meshes from the iai_apartment package, which lives as a subfolder in the
# code-iai/iai_maps repository (alongside iai_kitchen and others). It is
# registered the same way as the PR2 packages above.
RUN git clone --depth 1 https://github.com/code-iai/iai_maps.git \
    /home/${NB_USER}/ros_descriptions/iai_maps
RUN git config --global --add safe.directory /home/${NB_USER}/ros_descriptions/iai_maps
RUN touch /home/${NB_USER}/ament_prefix/share/ament_index/resource_index/packages/iai_apartment
RUN ln -s /home/${NB_USER}/ros_descriptions/iai_maps/iai_apartment \
    /home/${NB_USER}/ament_prefix/share/iai_apartment

# The apartment world also references the iai_kitchen package, another
# subfolder of the same already-cloned iai_maps repository.
RUN touch /home/${NB_USER}/ament_prefix/share/ament_index/resource_index/packages/iai_kitchen
RUN ln -s /home/${NB_USER}/ros_descriptions/iai_maps/iai_kitchen \
    /home/${NB_USER}/ament_prefix/share/iai_kitchen

# unzip is needed to extract the krrood archive below
USER root
RUN apt-get update && apt-get install -y unzip && rm -rf /var/lib/apt/lists/*
USER ${NB_USER}

# Download krrood (Entity Query Language + EQL-to-SQL translator) as source.
# A plain `git clone` fails with an authentication error in the Binder build
# environment, so a ZIP archive is downloaded via curl instead.
RUN curl -L https://github.com/cram2/cognitive_robot_abstract_machine/archive/refs/heads/main.zip \
    -o /tmp/krrood.zip \
    && unzip /tmp/krrood.zip -d /home/${NB_USER}/ \
    && mv /home/${NB_USER}/cognitive_robot_abstract_machine-main /home/${NB_USER}/krrood \
    && rm /tmp/krrood.zip

# Additional packages needed for the demo and the readability metrics
RUN pip install --no-cache-dir sqlalchemy pytest pandas matplotlib mujoco scikit-image piqp

# ROS2 system packages that semantic_digital_twin imports at runtime, but
# that are either unavailable on PyPI (rclpy_message_converter) or whose
# Python module lives under the ROS2 install path (xacro). The ROS2
# environment therefore has to be sourced before generate_orm.py runs
# (see below).
USER root
RUN apt-get update && \
    apt-get install -y ros-jazzy-xacro ros-jazzy-rclpy-message-converter && \
    rm -rf /var/lib/apt/lists/*
USER ${NB_USER}

# Optional adapter dependencies of semantic_digital_twin. Without these, ORM
# generation fails because krrood traverses every class in the package,
# including UsdSphereShapeBuilder (needs usd-core) and the Bullet physics
# collision checker (needs giskardpy_bullet_bindings). This line must come
# BEFORE the --force-reinstall lines below, otherwise it would overwrite the
# locally installed editable packages with older PyPI versions.
RUN pip install --no-cache-dir usd-core giskardpy_bullet_bindings

# The versions of krrood and semantic_digital_twin that pycram pulls in
# automatically from PyPI are older than the source code in this monorepo
# checkout and therefore incompatible with it (e.g. 'memoize' is missing
# from krrood.utils). Both are reinstalled from the local checkout, which
# overwrites the PyPI version. giskardpy and coraplex do not exist on PyPI
# at all and are installed exclusively from the local checkout. The order
# matters: krrood first (the base), then semantic_digital_twin, giskardpy,
# coraplex.
RUN pip install --no-cache-dir --force-reinstall --no-deps -e /home/${NB_USER}/krrood/krrood
RUN pip install --no-cache-dir --force-reinstall --no-deps -e /home/${NB_USER}/krrood/semantic_digital_twin
RUN pip install --no-cache-dir --no-deps -e /home/${NB_USER}/krrood/giskardpy

# giskardpy uses TYPE_CHECKING-only imports throughout many of its modules
# (a common pattern to avoid circular imports, meant for static type
# checkers like mypy). krrood's runtime ORM generation cannot resolve these,
# since it needs the referenced classes to be actually importable. Instead
# of patching each occurrence individually, this script scans the whole
# package and promotes every TYPE_CHECKING-only import to an unconditional
# one, handling multi-line parenthesized imports correctly via the ast module.
COPY scripts/patch_type_checking_imports.py /tmp/patch_type_checking_imports.py
RUN python3 /tmp/patch_type_checking_imports.py /home/${NB_USER}/krrood/giskardpy/src/giskardpy

# constraint.py originally imports EnforcementStrategy only under
# TYPE_CHECKING to avoid a genuine circular import, since
# enforcement_strategy.py already imports names from constraint.py
# unconditionally. Promoting this one specific import (as the general patch
# above does for everything) creates an unresolvable circular import that
# only manifests when giskardpy is entered through coraplex's import chain
# rather than giskardpy's own entry points. This step reverts just that one
# promotion, then appends the unconditional import at the very end of
# constraint.py instead, where every class the file defines already exists.
COPY scripts/fix_constraint_circular_import.py /tmp/fix_constraint_circular_import.py
RUN python3 /tmp/fix_constraint_circular_import.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/qp/constraint.py

COPY scripts/move_import_by_module_to_end.py /tmp/move_import_by_module_to_end.py

# NodeArtifacts (defined before MotionStatechartNode in graph_node.py) has a
# dataclass field `constraints: ConstraintCollection =
# field(default_factory=ConstraintCollection)`. This requires
# ConstraintCollection to be bound eagerly at class-definition time.
# ConstraintCollection's own module, however, transitively needs
# MotionStatechartNode back from this very file, which does not exist yet
# at that point, a genuine structural circular dependency that cannot be
# solved by import reordering alone. Wrapping the default factory in a
# lambda defers the reference to actual instance-creation time (long after
# all modules have finished loading), which means the ConstraintCollection
# import no longer needs to happen early and can safely be moved to the
# end of the file below, together with the other early imports.
COPY scripts/make_default_factory_lazy.py /tmp/make_default_factory_lazy.py
RUN python3 /tmp/make_default_factory_lazy.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/graph_node.py \
    ConstraintCollection

# graph_node.py imports several sibling giskardpy modules near the top of
# the file, before `class MotionStatechartNode` is defined. All of them
# directly or indirectly try to import MotionStatechartNode back from
# graph_node.py, causing a circular import. Each is moved individually to
# the end of the file, after MotionStatechartNode has been fully defined.
# The exceptions import is multi-line and parenthesized, so the AST-based
# module-name matcher is used instead of a literal single-line match.
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/graph_node.py \
    giskardpy.motion_statechart.constraint_builders
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/graph_node.py \
    giskardpy.motion_statechart.context
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/graph_node.py \
    giskardpy.motion_statechart.exceptions
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/graph_node.py \
    giskardpy.qp.constraint_collection
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/graph_node.py \
    giskardpy.motion_statechart.motion_statechart

# constraint_collection.py is imported early by graph_node.py. Two of its
# own imports indirectly or directly import MotionStatechartNode back from
# graph_node.py, causing the same kind of circular import one level deeper.
# Both are only used inside method bodies or as parameter type annotations
# in constraint_collection.py, never eagerly, so they are safe to move.
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/qp/constraint_collection.py \
    giskardpy.motion_statechart.exceptions
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/qp/constraint_collection.py \
    giskardpy.motion_statechart.graph_node

# exceptions.py's own back-imports of MotionStatechartNode and
# StillProgressing (promoted earlier by the general TYPE_CHECKING patch)
# each trigger a circular import via a different path than the one already
# fixed in graph_node.py itself: constraint_collection.py -> exceptions.py
# -> graph_node.py, and monitors/progress_monitors.py -> context.py ->
# exceptions.py respectively. Moving both to the end of exceptions.py
# resolves these remaining paths.
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/exceptions.py \
    giskardpy.motion_statechart.graph_node
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/exceptions.py \
    giskardpy.motion_statechart.monitors.progress_monitors

# motion_statechart.py has a mutual circular import with two of its own
# plotter modules (gantt_chart_plotter.py and graphviz.py): motion_statechart.py
# imports both at module level, while each of them imports MotionStatechart
# back (as a dataclass field type annotation). motion_statechart.py's use of
# both plotter classes is only inside method bodies (runtime calls, not
# eager defaults), so both imports are safe to move to the end of the file.
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/motion_statechart.py \
    giskardpy.motion_statechart.plotters.gantt_chart_plotter
RUN python3 /tmp/move_import_by_module_to_end.py \
    /home/${NB_USER}/krrood/giskardpy/src/giskardpy/motion_statechart/motion_statechart.py \
    giskardpy.motion_statechart.plotters.graphviz

RUN pip install --no-cache-dir --no-deps -e /home/${NB_USER}/krrood/coraplex

# The ORM interface files (e.g. coraplex/orm/ormatic_interface.py) are
# intentionally not committed to the repository and must be generated once.
# All four packages above must be fully installed before any of these
# scripts run, since semantic_digital_twin already references giskardpy at
# import time (a mutual dependency). Generation order: semantic_digital_twin
# first, then giskardpy, then coraplex. The ROS2 environment must be sourced
# so Python can find the ROS2-specific modules (xacro, rclpy_message_converter).
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && \
    cd /home/${NB_USER}/krrood/semantic_digital_twin && python3 scripts/generate_orm.py"
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && \
    cd /home/${NB_USER}/krrood/giskardpy && python3 scripts/generate_orm.py"
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && \
    cd /home/${NB_USER}/krrood/coraplex && python3 scripts/generate_orm.py"

# Resolve ROS2 dependencies for the remaining (genuine ROS2) packages in
# the workspace
USER root
RUN rosdep update && \
    rosdep install --from-paths ${ROS_WS}/src --ignore-src -r -y && \
    rosdep fix-permissions

USER ${NB_USER}
WORKDIR ${ROS_WS}
RUN colcon build --parallel-workers 4

# Automatically source the workspace when a terminal starts
RUN echo "source ${ROS_WS}/install/setup.bash" >> /home/${NB_USER}/.bashrc

# Copy the notebooks and the rest of the repository content into the image
USER ${NB_USER}
WORKDIR ${HOME}/work
COPY --chown=${NB_USER}:users ./ ${HOME}/work

# Take over the entrypoint (sources ROS_PATH automatically)
COPY --chown=${NB_USER}:users entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
CMD [ "start-notebook.sh" ]
