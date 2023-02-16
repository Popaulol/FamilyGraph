import argparse
import json
from typing import Optional
from pprint import pprint

from dataclasses import dataclass, field

# COLLAPSE SAME DIRECTED CONNECT TO SINGLE DOUBLY
# Allow mult files for everything
# Have Person configs


@dataclass
class Person:
    id: str
    name: Optional[str] = None
    incoming: list = field(default_factory=list)
    outgoing: list = field(default_factory=list)


connection_types = {}

people = {}


def add_connection_types(path: str):
    with open(path, "r", encoding="UTF-8") as f:
        connection_types.update(json.load(f))


def add_people(path: str):
    assert False


def parse(name: str):
    in_group = False
    with open(name, "r") as f:
        content = f.read()

    comment_depth = 0
    for row, line in enumerate(content.split("\n"), 1):
        if comment_depth >= 1:
            if line.startswith("/*"):
                comment_depth += 1
                continue
            elif line.endswith("*/"):
                comment_depth -= 1
            continue
        if line.startswith("//") or line.startswith("#"):
            continue
        elif line.startswith("/*"):
            comment_depth += 1
            continue
        elif in_group:
            # TODO: WRITTE GROUP STUFF
            pass
        elif line.startswith("include "):
            parse(line[8:].replace('"', "") + ".fam")
            print(line)
            continue
        elif line.startswith("config "):
            add_connection_types(line[7:].replace('"', "") + ".json")
            print(line)
            continue
        elif line.startswith("people "):
            add_people(line[7:].replace('"', "") + ".json")
            print(line)
            continue
        elif line == "{":
            in_group = True
        elif line == "":
            continue
        else:
            first_person = []
            operator = None
            index = None
            for i, word in enumerate(line.split(" ")):
                if word in connection_types:
                    operator = word
                    index = i
                    break
                first_person.append(word)
            else:
                exit(
                    f"Linie ohne konfigurierte Beziehung, die eine gebraucht hätte: `{name}`:{row} -> `{line}`"
                )
            first_person = " ".join(first_person)
            second_person = " ".join(line.split(" ")[index + 1 :])

            print(
                f"First Person: `{first_person}` Op: `{operator}` Second Person: `{second_person}`"
            )
            first_person_object = people.get(first_person, Person(first_person))
            second_person_object = people.get(second_person, Person(second_person))
            first_person_object.outgoing.append((operator, second_person_object))
            second_person_object.incoming.append((operator, first_person_object))
            people[first_person] = first_person_object
            people[second_person] = second_person_object


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="The file to render")
    parser.add_argument(
        "--infer-siblings", help="Should we infer siblings?", action="store_true"
    )
    parser.add_argument("--format", help="The output format", default="svg")
    args = parser.parse_args()

    parse(args.file)
    print(args)


if __name__ == "__main__":
    main()
