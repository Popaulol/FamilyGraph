# FamilyGraph
FamilyGraph is a tool to (hopefully) more easily describe family Trees and other Graph structures than writing dot files by hand but instead generating them from a similar DSL.

## Usage
This Project uses 3 basic files and filetypes to describe your graphs and relationships:
1. The `.fam` files conainting the actual Graph DSL and all of your relationships
2. The config file in `.json` format that describe attributes about the graph, mainly what kinds of connections exist
3. The People files also in `.json` format that describe the individual characters and their Attributes

### The `.fam` Syntax:
A .fam file consists of 3 basic types of lines
1. External file Statements
2. Connections
3. Group Control

You can seperate lines either by using a newline or a `;` character.

#### External file Statements
There are 3 Statements that load external files for usage:
```fam
include `file`
```
Statements include another .fam file (do not mention the extension in the statement) into the current one, placing all the connections made in that file into the current graph and enabling and overriding all other config changes that files does for the rest of you file as well.
<hr>

```fam
config `file`
```
Load a config File, to define new relationship operators to use. The format of these is described below. Note that you need to omit the `.json` extension in the Statement.
<hr>

```fam
people ``file
```
Load a config File, to define various aspects about the people. The format of these is described below. Note that you need to omit the `.json` extension in the Statement.

#### Connections
Connections are the most Essential Part of the Family Graph systems. These define the actual relationships between the people in your Tree based on the Types of connections defined in the config file.
The Syntax is:
```fam
Blub -> Blab
```
This line makes a connection between `Blub` and `Blab` based on what connection type `->` is currently defined from config files.  

#### Groups
Groups are meant to group a set of People together into a group.
In the final graph this these are circled in together in a circle.
Sadly because of graphviz restrictions, a single character cannot be in multiple Groups.
Groups are created by using curly braces `{}` and listing the people inside the group inside these, seperated either by `;` or newline.
Groups can also be given a name, by writing `name: 'name'` on a Line.

### config files
These are using the Standardized [JSON format](https://www.json.org/).
And they consist of a single High level Object, mapping the various operators/connection types the file defines to a few attributes Describing the Connection:
```json
{
    "->": {
        "title": "parents",
        "color": "green",
        "raw_attributes": "",
        "inference": null,
        "directed": true
    },
    "<->": {
        "title": "siblings",
        "color": "yellow",
        "raw_attributes": "",
        "inference": {
          "type": "sib",
          "parent_connection": "->"
        },
        "directed": false
    }
}
```
- `title: ` Every connection has a title that will be written on every Connection. If you do not want this to happen, simpy leave it as an Empty String.
- `color: ` The color the connection should have on the graph. This can be any string accepted by graphviz's [color Attribute](https://graphviz.org/docs/attrs/color/)
- `raw_attributes: ` The raw_attributes Attribute is currently unused and not even read by the project but might be in the future. If you want your files at least semi compatible with future version of this Project, you should include it and set it to an empty string, as shown in the example.
- `inference: ` Sets if and what type of Inference to use, and defines further Options for it. Inference is further explained below.
- `diected: ` Sets, if the Graph is directed or not, directed graphs point from one Node the other, whilst undirected edges do not have a direction associated with them.

### People files
Similar to config files, people files also using the Standardized [JSON format](https://www.json.org/).
They describe various Attributes of the Nodes/People in your graph:
```json
{
  "blub" : {
    "name": "Blub",
    "color": "Blue",
    "background-color": "black",
    "text-color": "gray"
  },
  "blab" : {
     "name": "Blab",
    "color": "Green"
  }
}
```
And they consist of a single High level Object, mapping the names/ids used for them in the `.fam` files to their attributes.
- `name: ` This is the name of the Person on the final Graph. This allows to use a shorter abbrivation in the source code whilst still being able to have long texts withing nodes if so desired.
- `color: ` This is the outline color the Person will have on the final Graph. This can be any string accepted by graphviz's [color Attribute](https://graphviz.org/docs/attrs/color/)
- `background-color: ` The Background color of the Node
- `text-color: ` The Text Colour of the Node

All of these Attributes can just be left out, then the default value will be used.

## Handling of conflicts
When there are conflicting Options, the last one defined is the one that is used.