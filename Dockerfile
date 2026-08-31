FROM intel4coro/jupyter-ros2:jazzy-py3.12

USER ${NB_USER}
ENV ROS_WS=/home/${NB_USER}/ros2_ws

# ROS2-Workspace anlegen
RUN mkdir -p ${ROS_WS}/src
WORKDIR ${ROS_WS}/src

# pycram klonen
RUN git clone --depth 1 https://github.com/cram2/pycram.git

RUN git config --global --add safe.directory ${ROS_WS}/src/pycram

RUN pip install --no-cache-dir -e ${ROS_WS}/src/pycram

# krrood (Entity Query Language + EQL-zu-SQL-Übersetzer) installieren
RUN git clone --depth 1 https://github.com/cram2/cognitive_robot_abstract_machine.git /home/${NB_USER}/krrood
RUN pip install --no-cache-dir -e /home/${NB_USER}/krrood/krrood
RUN pip install --no-cache-dir -e /home/${NB_USER}/krrood/giskardpy
RUN pip install --no-cache-dir sqlalchemy pytest pandas matplotlib mujoco

# ROS2-Abhängigkeiten auflösen und den Workspace bauen
USER root
RUN rosdep update && \
    rosdep install --from-paths ${ROS_WS}/src --ignore-src -r -y && \
    rosdep fix-permissions

USER ${NB_USER}
WORKDIR ${ROS_WS}
RUN colcon build --parallel-workers 4

# Workspace beim Terminal-Start automatisch sourcen
RUN echo "source ${ROS_WS}/install/setup.bash" >> /home/${NB_USER}/.bashrc

# Notebooks und restlichen Repo-Inhalt reinkopieren
USER ${NB_USER}
WORKDIR ${HOME}/work
COPY --chown=${NB_USER}:users ./ ${HOME}/work

# Entrypoint übernehmen (sourced ROS_PATH automatisch, wie in deinem entrypoint.sh)
COPY --chown=${NB_USER}:users entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
CMD [ "start-notebook.sh" ]
