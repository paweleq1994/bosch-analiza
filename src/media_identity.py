from __future__ import annotations


def canonicalize_player_media(manifest: dict, aliases: dict[str, str]) -> dict:
    merged_subjects: dict[tuple[str, str], dict] = {}
    photo_ids_by_subject: dict[tuple[str, str], set[str]] = {}

    for subject in manifest.get("subjects") or []:
        kind = str(subject["kind"])
        source_id = str(subject["id"])
        canonical_id = aliases.get(source_id, source_id) if kind == "players" else source_id
        subject_key = (kind, canonical_id)

        if subject_key not in merged_subjects:
            merged_subjects[subject_key] = {"kind": kind, "id": canonical_id, "photos": []}
            photo_ids_by_subject[subject_key] = set()

        for photo in subject.get("photos") or []:
            photo_id = str(photo.get("id") or "")

            if not photo_id or photo_id in photo_ids_by_subject[subject_key]:
                continue

            record = dict(photo)

            if kind == "players" and source_id != canonical_id:
                record["source_player_id"] = source_id

            merged_subjects[subject_key]["photos"].append(record)
            photo_ids_by_subject[subject_key].add(photo_id)

    return {**manifest, "subjects": list(merged_subjects.values())}
