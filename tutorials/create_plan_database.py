"""
Erzeugt die Plan-Datenbanken, auf denen die Plan-Beispiele in eql_show.ipynb laufen.

Wird einmalig ausgefuehrt (nicht im Notebook):

    python create_plan_database.py          # plan_result.sqlite
    python create_plan_database.py --rich   # plan_result_rich.sqlite (zusaetzlich: Milch mit rechtem Arm)

Der Plan (ParkArms, MoveTorso, TransportAction Schale/Loeffel mit dem linken Arm,
in der Variante --rich zusaetzlich TransportAction Milch mit dem rechten Arm) wird
in der Simulation ausgefuehrt und mit to_dao(plan) in SQLite gespeichert.
"""
import argparse
import os

from sqlalchemy.orm import Session

import coraplex.orm.ormatic_interface as coraplex_orm
from coraplex.datastructures.dataclasses import Context
from coraplex.datastructures.enums import Arms, ApproachDirection, VerticalAlignment
from coraplex.datastructures.grasp import GraspDescription
from coraplex.execution_environment import simulated_robot
from coraplex.plans.factories import sequential
from coraplex.robot_plans.actions.composite.transporting import TransportAction
from coraplex.robot_plans.actions.core.robot_body import ParkArmsAction, MoveTorsoAction
from coraplex.testing import setup_world

from krrood.entity_query_language.factories import an, entity, variable
from krrood.ormatic.data_access_objects.helper import to_dao
from krrood.ormatic.utils import create_engine

from semantic_digital_twin.adapters.mesh import STLParser
from semantic_digital_twin.datastructures.definitions import TorsoState
from semantic_digital_twin.reasoning.world_reasoner import WorldReasoner
from semantic_digital_twin.robots.pr2 import PR2
from semantic_digital_twin.semantic_annotations.semantic_annotations import (
    Bowl, Spoon, Milk, Drawer, Handle,
)
from semantic_digital_twin.spatial_types import HomogeneousTransformationMatrix
from semantic_digital_twin.spatial_types.spatial_types import Pose
from semantic_digital_twin.world_description.connections import FixedConnection

RESOURCES = "/home/jovyan/krrood/coraplex/resources/objects"
OUTPUT_DIR = "/home/jovyan/work/tutorials"


def build_plan(rich: bool):
    world = setup_world()
    spoon = STLParser(f"{RESOURCES}/spoon.stl").parse()
    bowl = STLParser(f"{RESOURCES}/bowl.stl").parse()

    with world.modify_world():
        world.merge_world_at_pose(
            bowl,
            HomogeneousTransformationMatrix.from_xyz_quaternion(
                2.4, 2.2, 1, reference_frame=world.root
            ),
        )
        connection = FixedConnection(
            parent=world.get_body_by_name("cabinet10_drawer_top"),
            child=spoon.root,
            parent_T_connection_expression=HomogeneousTransformationMatrix.from_xyz_rpy(
                -0.05, -0.05, 0
            ),
        )
        world.merge_world(spoon, connection)

    pr2 = PR2.from_world(world)
    context = Context(world=world, robot=pr2, _debug=False, ros_node=None)

    with world.modify_world():
        WorldReasoner(world).reason()
        world.add_semantic_annotations([
            Bowl(root=world.get_body_by_name("bowl.stl")),
            Spoon(root=world.get_body_by_name("spoon.stl")),
        ])
        world.add_semantic_annotation_recursively(
            Drawer(
                root=world.get_body_by_name("cabinet10_drawer_top"),
                handle=Handle(root=world.get_body_by_name("handle_cab10_t")),
            )
        )

    context.evaluate_conditions = False

    def find(cls):
        return next(an(entity(variable(cls, domain=world.semantic_annotations))).evaluate())

    bowl_annotation, spoon_annotation = find(Bowl), find(Spoon)

    steps = [
        ParkArmsAction(Arms.BOTH),
        MoveTorsoAction(TorsoState.HIGH),
        TransportAction(
            bowl_annotation,
            Pose.from_xyz_rpy(5, 3.3, 0.75, yaw=1.57, reference_frame=world.root),
            Arms.LEFT,
        ),
        TransportAction(
            spoon_annotation,
            Pose.from_xyz_rpy(5.1, 3.3, 0.75, yaw=1.57, reference_frame=world.root),
            Arms.LEFT,
            GraspDescription(
                ApproachDirection.FRONT,
                VerticalAlignment.TOP,
                pr2.left_arm.end_effector,
            ),
        ),
    ]
    if rich:
        # milk.stl wird bereits von setup_world() annotiert, hier nur nachgeschlagen
        steps.append(
            TransportAction(
                find(Milk),
                Pose.from_xyz_rpy(4.7, 3.3, 0.75, yaw=1.57, reference_frame=world.root),
                Arms.RIGHT,
            )
        )
    return sequential(steps, context=context).plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rich", action="store_true",
                        help="zusaetzlich Milch mit dem rechten Arm transportieren")
    args = parser.parse_args()

    name = "plan_result_rich.sqlite" if args.rich else "plan_result.sqlite"
    path = os.path.join(OUTPUT_DIR, name)

    plan = build_plan(args.rich)
    with simulated_robot:
        plan.perform()
    for node in plan.nodes:
        print(f"{node.__class__.__name__}: {node.status.name}")

    if os.path.exists(path):
        os.remove(path)  # frisch erzeugen, damit der Plan nicht doppelt drin steht
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    coraplex_orm.Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(to_dao(plan))
        session.commit()
    print(f"\nPlan saved to {path}")


if __name__ == "__main__":
    main()
