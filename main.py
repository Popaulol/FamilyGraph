from __future__ import annotations
import argparse
import builtins
import enum
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional
from pprint import pprint

from dataclasses import dataclass, field

count = 0

silent = False
verbosity = 0


def silent_print(*args, **kwargs):
    if silent:
        return

    return builtins.print(*args, **kwargs)


def verbosity_print(*args, level, **kwargs):
    if silent:
        return

    if verbosity < level:
        return

    return builtins.print(*args, **kwargs)


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
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    image: Optional[str] = None


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
        person.background_color = data.get("background-color", person.background_color)
        person.text_color = data.get("text-color", person.text_color)
        person.image = data.get("image", person.image)
        people[fam_id] = person


def parse(name: str):
    in_group = False
    current_group = None

    file = Path(name).resolve(strict=True)
    cwd = os.getcwd()
    os.chdir(file.parent)

    assert file.is_file(), "You need to Pass a file, not a directory."

    with open(file, "r") as f:
        content = f.read()

    comment_depth = 0
    for row, line in enumerate(re.split("\n|;", content), 1):
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
            verbosity_print(f"Parsing include:\t`{line}`", level=2)
            continue
        elif line.startswith("config "):
            add_connection_types(line[7:].replace('"', "") + ".json")
            verbosity_print(f"Parsing config:\t`{line}`", level=2)
            continue
        elif line.startswith("people "):
            add_people(line[7:].replace('"', "") + ".json")
            verbosity_print(f"Parsing people Statement:\t`{line}`", level=2)
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

            verbosity_print(
                f"Parsing Connection: First Person: `{first_person}` Op: `{operator}` Second Person: `{second_person}`",
                level=3)

            first_person_object = people.get(first_person, Person(first_person))
            second_person_object = people.get(second_person, Person(second_person))
            conn = Connection(operator, first_person_object, second_person_object)
            first_person_object.outgoing.append(conn)
            second_person_object.incoming.append(conn)
            people[first_person] = first_person_object
            people[second_person] = second_person_object

    os.chdir(cwd)


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

    verbosity_print(f"Count of Connections before deletion {len(connections)}", level=1)
    for connection in deleted:
        try:
            connections.remove(connection)
            connection.target.incoming.remove(connection)
            connection.origin.outgoing.remove(connection)
        except Exception as e:
            verbosity_print(f"Exception Occured during Connection deletion, this is could be expected but might be a "
                            f"bug {e}", level=1)
    verbosity_print(f"Count of Connections after deletion {len(connections)}", level=1)
    verbosity_print(f"Count of Connections deletiod {len(deleted)}", level=1)


def generate_dot_file(name: str):
    print(name)
    newline = "\n"
    with open(name, "w") as f:
        f.write("digraph Tree {\n")

        for person in people.values():
            color = f'color="{person.color}"' if person.color else ""
            label = f'label="{person.name or person.fam_id}"'
            bg_color = f'fillcolor="{person.background_color}"' if person.background_color else ""
            txt_color = f'fontcolor="{person.text_color}"' if person.text_color else ""
            image = f'''image="{person.image}"
                            imagescale=both''' if person.image else ""
            f.write(f"""{person.dot_id} [{newline.join(attr for attr in (color, label, bg_color, txt_color, image,
                                                                         "style=filled") if attr)}]\n""")

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
    parser.add_argument(
        "--no-dot", help="Do not run Graphviz on the generated dot-file", action="store_false"
    )
    parser.add_argument("--format", help="The output format", default="png")
    parser.add_argument("--layout", help="The dot Layout Engine to use", default="dot")
    parser.add_argument("--silent", help="Should we just stay fully silent?", action="store_true")
    parser.add_argument("-v", "--verbose", help="Should we print various debugging output? Repeat this option more often, to get more Output.", action="count", default=0)
    args = parser.parse_args()

    global silent, verbosity
    silent = args.silent
    verbosity = args.verbose

    parse(args.file)
    fixup_connections()
    pprint(connection_types)

    if args.infer:
        infer()
        fixup_connections()
    generate_dot_file(args.file + ".dot")

    if args.no_dot:
        path = Path(args.file + ".dot").resolve()
        os.chdir(path.parent)

        command = ["dot", f"-T{args.format}", f"-K{args.layout}", "-O", str(path)]
        silent_print(f"Calling dot: `{' '.join(command)}`")
        subprocess.call(command)


if __name__ == "__main__":
    main()
