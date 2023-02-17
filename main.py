from __future__ import annotations
import argparse
import enum
import json
import subprocess
from typing import Optional
from pprint import pprint

from dataclasses import dataclass, field

count = 0


def generate_uuid():
    global count
    count += 1
    return "id_" + hex(count)


connections: list[Connection] = []


def auto_add(collection):
    def inner(cls):
        def old_post_init(*args, **kwargs):
            return None

        if hasattr(cls, "__post_init__"):
            old_post_init = cls.__post_init__

        def wrapper(self, *args, **kwargs):
            collection.append(self)
            return old_post_init(self, *args, **kwargs)

        cls.__post_init__ = wrapper
        return cls

    return inner


# COLLAPSE SAME DIRECTED CONNECT TO SINGLE DOUBLY
# Allow mult files for everything
# Have Person configs

class Direction(enum.Enum):
    UNDIRECTED = enum.auto()
    DIRECTED = enum.auto()
    BIDIRECTED = enum.auto()


@dataclass
@auto_add(connections)
class Connection:
    op: str
    origin: Person
    target: Person
    directed: Optional[Direction] = None
    title: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    inference: Optional[dict[str, str]] = None

    def __hash__(self):
        return id(self)


@dataclass
class Person:
    fam_id: str
    name: Optional[str] = None
    incoming: list[Connection] = field(default_factory=list)
    outgoing: list[Connection] = field(default_factory=list)
    dot_id: str = field(default_factory=generate_uuid)
    color: Optional[str] = None


@dataclass
class Group:
    name: Optional[str] = None
    members: list[Person] = field(default_factory=list)
    dot_id: str = field(default_factory=generate_uuid)


connection_types = {}

people = {}

groups = []


def add_connection_types(path: str):
    with open(path, "r", encoding="UTF-8") as f:
        connection_types.update(json.load(f))


def add_people(path: str):
    # TODO: Add more Person attributes
    with open(path, "r") as f:
        peeps = json.load(f)

    for fam_id, data in peeps.items():
        person = people.get(fam_id, Person(fam_id))
        person.name = data.get("name", person.name)
        person.color = data.get("color", person.color)
        people[fam_id] = person


def parse(name: str):
    in_group = False
    current_group = None
    with open(name, "r") as f:
        content = f.read()

    comment_depth = 0
    for row, line in enumerate(content.split("\n"), 1):
        line = line.strip()
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
            if line.startswith("}"):
                in_group = False
                groups.append(current_group)
                continue
            elif line.startswith("{"):
                exit(
                    f"Keine Gruppen in Gruppen: `{name}`:{row} -> `{line}`"
                )
            elif ":" in line:
                attribute, *rest = line.split(":")
                rest = ":".join(rest)
                if attribute == "name":
                    current_group.name = rest
                continue

            current_group.members.append(people.get(line.strip(), Person(line.strip())))

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
        elif line.startswith("{"):
            in_group = True
            current_group = Group()
        elif line == "":
            continue
        else:
            first_person = []
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
            second_person = " ".join(line.split(" ")[index + 1:])

            print(
                f"First Person: `{first_person}` Op: `{operator}` Second Person: `{second_person}`"
            )
            first_person_object = people.get(first_person, Person(first_person))
            second_person_object = people.get(second_person, Person(second_person))
            conn = Connection(operator, first_person_object, second_person_object)
            first_person_object.outgoing.append(conn)
            second_person_object.incoming.append(conn)
            people[first_person] = first_person_object
            people[second_person] = second_person_object


def fixup_connections():
    deleted = set()
    for connection in connections:
        if connection in deleted:
            continue
        definition = connection_types[connection.op]
        connection.title = definition.get("title", None)
        connection.color = definition.get("color", None)
        connection.style = definition.get("style", None)
        connection.inference = definition.get("inference")

        if definition["directed"]:
            connection.directed = Direction.DIRECTED
        else:
            connection.directed = Direction.UNDIRECTED

        for conn in connection.target.outgoing:
            if conn.op != connection.op:
                continue
            if conn.target is connection.origin and conn.origin is connection.target:
                if connection.directed == Direction.DIRECTED:
                    connection.directed = Direction.BIDIRECTED
                deleted.add(conn)

        for conn in connection.origin.outgoing:
            if conn.op != connection.op:
                continue
            if conn.target is connection.target and conn.origin is connection.origin and conn is not connection:
                deleted.add(conn)

    print(len(connections))
    for connection in deleted:
        try:
            connections.remove(connection)
            connection.target.incoming.remove(connection)
            connection.origin.outgoing.remove(connection)
        except Exception as e:
            print(e)
    print(len(connections))
    print(len(deleted))


def generate_dot_file(name: str):
    with open(name, "w") as f:
        f.write("digraph Tree {\n")

        for person in people.values():
            f.write(f"""{person.dot_id} [
            color="{person.color}"
            label="{person.name or person.fam_id}"
            ]
        """)

        for connection in connections:
            """
    directed: Optional[Direction] = None
            """
            if connection.directed is Direction.UNDIRECTED:
                start, end = "none", "none"
            elif connection.directed is Direction.DIRECTED:
                start, end = "none", "normal"
            elif connection.directed is Direction.BIDIRECTED:
                start, end = "normal", "normal"
            elif connection.directed is None:
                start, end = "none", "none"
            else:
                assert False, "WTF"
            f.write(f"""{connection.origin.dot_id} -> {connection.target.dot_id} [
                {('label="' + connection.title + '"') if connection.title is not None else ""}
                {('style="' + connection.style + '"') if connection.style is not None else ""}
                {('color="' + connection.color + '"') if connection.color is not None else ""}
                arrowhead="{end}"
                arrowtail="{start}"
            ]
            """)

        newline = "\n"
        for group in groups:
            f.write(f"""subgraph cluster_{generate_uuid()} {{
                {newline.join(map(lambda p: p.dot_id, group.members))}
                label="{group.name}"
            }}
        """)
        f.write("}")


def infer():
    for key, connection_type in connection_types.items():
        if not connection_type["inference"]:
            continue
        elif connection_type["inference"]["type"] == "sib":
            for person in people.values():
                people_to_add = []
                for connection in person.incoming:
                    if connection.op == connection_type["inference"]["parent_connection"]:
                        for conn in connection.origin.outgoing:
                            if conn.op == connection_type["inference"]["parent_connection"]:
                                people_to_add.append(conn.target)
                for peep in people_to_add:
                    # print("aqs")
                    conn = Connection(key, person, peep)
                    person.outgoing.append(conn)
                    peep.incoming.append(conn)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="The file to render")
    parser.add_argument(
        "--infer", help="Should we try to infer things?", action="store_true"
    )
    parser.add_argument("--format", help="The output format", default="svg")
    args = parser.parse_args()

    parse(args.file)
    fixup_connections()
    pprint(connection_types)

    if args.infer:
        infer()
        fixup_connections()
    generate_dot_file(args.file + ".dot")

    subprocess.call(["dot", "-Tsvg", "-O", args.file + ".dot"])


if __name__ == "__main__":
    main()
