def get_tags_from_script(script: str) -> list[str]:
    # Split the content based on the separator
    if "####" not in script:
        raise ValueError("No '####' separator found in the response.")

    # Assuming the separator is "#####\n"
    parts = script.split("#####", 1)
    if len(parts) < 2:
        raise ValueError("No tags found after '#####' separator.")

    tag_part = parts[1].strip()

    # The tag_part might start with a newline, strip it
    # Now split by commas
    tags = [tag.strip() for tag in tag_part.split(",") if tag.strip()]

    if not tags:
        raise ValueError("No valid tags found after '####' separator.")

    return tags