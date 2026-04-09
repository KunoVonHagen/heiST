import subprocess
from typing import List
import psycopg2

from .cleanup import teardown_remaining_challenges
from .proxmox_api_calls import delete_vm_api_call
from .DatabaseClasses import ChallengeTemplate, MachineTemplate, Challenge
from .get_db_connection import db_connection_context


def delete_machine_templates(challenge_template_id: int) -> None:
    """
    Delete the machine template VMs for a challenge.
    """

    with db_connection_context() as db_conn:
        try:
            disable_pooling_for_challenge_template(challenge_template_id, db_conn)

            challenge_template: ChallengeTemplate = fetch_challenge_and_machine_templates(challenge_template_id, db_conn)

            challenges: List[Challenge] = fetch_running_challenges(challenge_template, db_conn)
        except Exception as e:
            raise ValueError(f"Error fetching challenge and machine templates: {str(e)}")

        teardown_remaining_challenges([challenge.id for challenge in challenges])

        delete_machine_template_vms(challenge_template)


def disable_pooling_for_challenge_template(challenge_template_id: int, db_conn: psycopg2.extensions.connection) -> None:
    """
    Disable pooling for a challenge template.
    """

    with db_conn.cursor() as cursor:
        cursor.execute("UPDATE challenge_templates SET ready_to_launch = FALSE WHERE id = %s", (challenge_template_id,))
        db_conn.commit()


def fetch_challenge_and_machine_templates(challenge_template_id: int, db_conn: psycopg2.extensions.connection) -> ChallengeTemplate:
    """
    Fetch the machine template IDs for a challenge.
    """

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM challenge_templates WHERE id = %s", (challenge_template_id,))

        result: tuple[int] | None = cursor.fetchone()
        if result is None:
            raise ValueError(f"Challenge template with ID {challenge_template_id} not found.")

        challenge_template: ChallengeTemplate = ChallengeTemplate(challenge_template_id=challenge_template_id)

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM machine_templates WHERE challenge_template_id = %s", (challenge_template.id,))

        for machine_template_id_row in cursor.fetchall():
            machine_template: MachineTemplate = MachineTemplate(
                machine_template_id=machine_template_id_row[0],
                challenge_template=challenge_template
            )
            challenge_template.add_machine_template(machine_template)

    return challenge_template


def fetch_running_challenges(challenge_template: ChallengeTemplate, db_conn: psycopg2.extensions.connection) -> List[Challenge]:
    """
    Fetch the running machine template instances for a challenge.
    """

    challenges: List[Challenge] = []

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id, subnet FROM challenges WHERE challenge_template_id = %s", (challenge_template.id,))

        for challenge_id, subnet in cursor.fetchall():
            challenge: Challenge = Challenge(challenge_id=challenge_id, template=challenge_template, subnet=subnet)
            challenges.append(challenge)

    return challenges


def delete_machine_template_vms(challenge_template: ChallengeTemplate) -> None:
    """
    Delete the machine template VMs for a challenge.
    """

    for machine_template in challenge_template.machine_templates.values():
        try:
            delete_vm_api_call(machine_template)
        except Exception:
            subprocess.run(["qm", "stop", str(machine_template.id)], check=False, capture_output=True)
            subprocess.run(["qm", "unlock", str(machine_template.id)], check=True, capture_output=True)
            subprocess.run(["qm", "destroy", str(machine_template.id)], check=True, capture_output=True)
