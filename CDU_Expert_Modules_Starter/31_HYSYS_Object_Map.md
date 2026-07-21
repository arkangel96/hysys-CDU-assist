# HYSYS Object Mapping

## Purpose
Define a stable abstraction layer between Aspen HYSYS objects and the expert system.

## Mapping Philosophy
The reasoning engine must never directly depend on HYSYS UI names.
Instead it interacts with logical engineering objects.

Example:

Engineering Object
- Fired Heater Outlet Temperature

HYSYS Object
- Energy Stream
- Heater Block
- Outlet Stream Temperature

## Required Mapping

For every equipment define:
- Object ID
- Type
- Inputs
- Outputs
- Specifications
- Degrees of freedom
- Read-only variables
- Writable variables
- Constraints

## Interface Contract

Every object shall expose:

- ReadState()
- Validate()
- CalculateDerivedVariables()
- ApplyAction()
- Rollback()

## Future Expansion

Include every CDU object:
- Streams
- Heat Exchangers
- Columns
- Side strippers
- Pumps
- Valves
- Controllers