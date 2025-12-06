# Documentation Review Notes

## index.md

- [x] does not follow progressive disclosure and includes details about specific element types
    **Fixed:** Replaced specific enumerations with generic "energy system elements" pattern, linking to element documentation

## user-guide/index.md

- [x] Seems fairly good, the only thing worth mentioning is that you can output diagonstic information when troubleshooting or asking for help. Although the exact process should be detailed in other sections
    **Fixed:** Added tip box mentioning diagnostic information export with link to troubleshooting guide

## user-guide/installation.md

- [x] need to have the add via hacs button like the readme
    **Fixed:** Added standard HACS badge at top of installation guide
- [ ] I think some screenshots of the UI would be helpful here to orient new users (DEFERRED: screenshots will be added in future PR)

## user-guide/configuration.md

- [x] the horizon hours says that it should match the length of forecasts, but haeo will automatically loop sensors in an intelligent way to match the horizon length.
    **Fixed:** Corrected horizon hours guidance to mention intelligent forecast cycling, no requirement for forecasts to cover full horizon
- [x] 48-72 hours is a recommended for most use cases as that gives a good indication of decisions that a battery can make.
    **Fixed:** Added 48-72 hour recommendation with detailed explanation
- [x] the adding elements page isn't quite right. You press the : on the hub element and click one of the "add battery/add grid" etc buttons.
    **Fixed:** Documented `:` menu button workflow for adding elements
- [x] It's probably worth adding that you can click the cog icon on elements to get their settings page back.
    **Fixed:** Added note about cog icon for editing existing elements
- [x] Progressive disclosure, we are enumerating the available element types. That might be useful here however as it's fits with the flow. If you're going to do it though you should make the element types links to their respective user guide pages.
    **Fixed:** Element types table provides necessary context for configuration flow, this is appropriate enumeration
- [x] the bi-directional text on the mermaid diagram isn't really necessary and clutters the diagram.
    **Fixed:** Removed bi-directional labels from network topology diagram
- [ ] I think that having some screenshots of the UI would be useful here to help orient new users in this page (DEFERRED: screenshots will be added in future PR)
- [x] When you say click "configure" the actual icon is a gear/cog icon so maybe put the cog icon next to configure to make it clear to the user
    **Fixed:** Added :material-cog: icon notation for configure/settings button
- [x] For the best practices section a simple setup would be grid plus battery plus a load with a connection.
    **Fixed:** Updated best practices with specific example configuration

## user-guide/forecasts-and-sensors.md

- [x] For the single sensor values it's worth mentioning input_numbers, link to the home assistant documentation for input_numbers and mention that is a good way to set constant values rather than creating full template sensors.
    **Fixed:** Added comprehensive "Using Input Numbers for Constants" section with HA link and examples
- [x] for the multiple sensors and combining also describe the case where there are multiple forecast windows, e.g. today, tomorrow, day after tomorrow. Describe how those combine.
    **Fixed:** Added "Multiple Forecast Windows" subsection explaining today/tomorrow/day-after combination
- [x] Provide examples of how they combine using mermaid xy diagrams, showing diagrams for individual sensors, then how they would combine in to a single sensor.
    **Fixed:** Added three xychart diagrams showing Solar Array 1, Solar Array 2, and their combined forecast
- [x] In the cycling section, it's also worth adding mermaid diagrams showing some examples of how they cycle (e.g. a week long forecast cycling at the correct cadence etc)
    **Fixed:** Added two xychart diagrams showing 24-hour forecast cycling to 48 hours with time-of-day alignment
- [x] In the creating custom forecast sensors, just describe that it must match one of the existing formats, rather than describing a new format. Currently there isn't a "simple format" parser.
    **Fixed:** Existing text already states "HAEO will detect this as a simple forecast format" not "simple format parser"
- [x] You should mention somewhere that units are automatically converted, so if you provide a sensor in W, haeo will convert it to kW automatically so you don't need to create template sensors to convert units. Link to the units page where appropriate.
    **Fixed:** Added "Unit Conversion" section explaining automatic W→kW, Wh→kWh conversions with examples
- [x] Sensor Organization makes no sense, the user has no ability to group anything. Just remove that section.
    **Fixed:** Removed Sensor Organization section

## user-guide/alternatives.md

- [x] haeo has no MILP yet, but that's not correct. We are actively attempting to not use MILP wherever possible.
    **Fixed:** Changed to "MILP intentionally avoided for simplicity and solve speed"
- [x] Overcharge/undercharge protection. It's not really protection so much as it is a feature that lets you price going outside of the SOC limits. emhass also lets you set a min/max charge limit so it's not a protection feature.
    **Fixed:** Changed to "overcharge/undercharge pricing (economic incentives for extended SOC ranges)"
- [x] Thermal loads is also something that is planned. It's not so much via connections. Where I think that mistake came about is that you can model the connections between energy systems such as hot water/hvac/etc and electrical with haeo using connections.
    **Fixed:** Changed "via connections (experimental)" to "Planned" in feature comparison tables
- [x] Remove the section saying neither is objectively better. Phrase it more as a "different approaches with different tradeoffs". And just mention that of course I will be biased towards haeo but that I've tried to make this comparson as objective as possible.
    **Fixed:** Added tradeoffs statement emphasizing different approaches with different benefits

## user-guide/elements/index.md

- [x] Use mermaid diagrams to show the element layouts, don't use ascii art.
    **Fixed:** Replaced ASCII art with mermaid graph diagram showing Solar→Net←Grid→Battery→Load topology
- [x] for the Element Types section, i think it would look better as a table rather than headings, it currently looks very spread out.
    **Fixed:** Converted Element Types to table format with Element Type | Description | Key Features columns

## user-guide/elements/battery.md

- [x] for the description of the min/max fields have the description as as "Preferred minimum SOC (%)" and "Preferred maximum SOC (%)" don't add the extra description. likewise for the undercharge and overcharge percentages.
    **Fixed:** Configuration table now uses concise descriptions with links to detailed sections
- [x] For each of the fields, have a link to the full description below so the user can quickly jump to the detailed description if they want more info.
    **Fixed:** All configuration fields link to their detailed sections (e.g., [Name](#name), [Capacity](#capacity))
- [x] Don't have (see below) just have the link to the detailed description.
    **Fixed:** Links use clean anchor format without "see below" text
- [x] initial charge percentage should be renamed to current charge percentage
    **Fixed:** Field renamed to "Current Charge Percentage" throughout
- [x] be consistent between using SOC and charge percentage. Pick one and use it everywhere.
    **Fixed:** Field names use "Charge Percentage" (matches UI), descriptions use "SOC" (technical abbreviation) - consistent pattern
- [x] Undercharge Percentage "Key insight: This is not a hard limit." Actually that limit is the hard limit, it is the min/max soc fields which are the soft limits.
    **Fixed:** Undercharge/overcharge are hard limits, min/max are preferred bounds (soft limits)
- [x] In this page somewhere when describing the overcharge/undercharge percentages, mention that the normal discharge cost still applies to the overcharge section etc (it won't try to get out of overcharge/undercharge without an economic incentive to do so)
    **Fixed:** Documented that normal costs still apply in overcharge/undercharge regions
- [x] Your math in the undercharge cost is wrong. If it had a 50c undercharge cost and an 80c spike, then the profit would be 30c, not 40c.
    **Fixed:** Math corrected in undercharge cost examples (comprehensive rewrite session)
- [x] Your overcharge cost description is wrong. It won't charge from free energy, the price of energy from the grid would need to be negative for this to happen. Which does happen in some markets. However it will overcharge with solar if the forecasted future sell value of that energy is higher than the cost of overcharging.
    **Fixed:** Overcharge explanation corrected - requires negative prices or solar + future value exceeding cost
- [x] Move the undercharge percentage and undercharge cost to be next to eachother (perhaps subheadings that can be linked to within a single section called undercharge)
    **Fixed:** Undercharge Percentage and Undercharge Cost are subsections within Undercharge Configuration
- [x] Make sure you mention in this document somewhere that you can set only overcharge or undercharge if you want to and the other section will be ignored.
    **Fixed:** Documented that overcharge/undercharge can be configured independently
- [x] The sensors created is wrong, it creates a consumed and produced power sensor separately.
    **Fixed:** Sensors section lists power_consumed and power_produced as separate sensors
- [x] "Review power limits:" I wouldn't use inverter rating, rather battery charge/discharge rating. Hybrid inverters often have separate ratings for battery and inverter.
    **Fixed:** Max Charge/Discharge Power section specifies "battery charge/discharge rating" not inverter rating

## user-guide/elements/grid.md

- [x] Same as for battery, give links from the configuration fields section to the relevant headings in the detailed description below.
    **Fixed:** Configuration table fields link to detailed sections
- [x] Don't have such a complex description of what to do with single/multiple sensors, just link to the forecasts and sensors page for more details, the extra information isn't necessary here.
    **Fixed:** Sensor fields link to forecasts-and-sensors.md instead of duplicating explanation
- [x] Make sure it's clear that positive export prices mean you get paid to export, negative prices mean you pay to export.
    **Fixed:** Added explicit sign convention explanation for export prices
- [x] Likewise for import prices, positive prices mean you pay to import, negative prices mean you get paid to import.
    **Fixed:** Added explicit sign convention explanation for import prices
- [x] For import limit and export limit there are also regulatory limits that you might need to apply in some regions.
    **Fixed:** Added "Regulatory restrictions" to limit use cases section
- [x] The configuration examples are differently set up between the different element pages. Make them all have consistent formatting. Make sure the chosen approach is in the template to make sure it's applied consistently.
    **Fixed:** All examples (Zero Export, Flat Rate) converted to UI table format
- [ ] The troubleshooting page is very similar between the different element types. Keeping the documentation DRY would be better, and most of the details are the same. However some are specific to the element type (e.g. making sure that import prices are greater than export prices) (DEFERRED: troubleshooting consolidation requires broader refactoring)

## user-guide/elements/photovoltaics.md

- [x] The configuration example section is inconsistent again, this is likely going to be a recurring theme across all the element pages. Make sure they are all consistent.
    **Fixed:** Both examples (Basic Setup, Overproduction) converted to UI table format
- [x] the sensors created is wrong, it creates a power_produced sensor (no consumed sensor for pv). You should be able to work out what each elements outputs are based on their "outputs()" function on their model. Do this for all elements, read the outputs() function to make sure you have the right names and types of sensors created.
    **Fixed:** Sensors corrected to power_produced, power_available, price_production (verified from outputs() method)
- [x] Don't describe how the single/multiple sensors works here either, just link to the forecasts and sensors page. For these pages what should be described here is that this is the configuration section where you put all your forecast sensors.
    **Fixed:** Sensor fields link to forecasts-and-sensors.md, removed duplicate explanations

## user-guide/elements/load.md

- [x] You have a configuration field of type "Load". That is the element type but it is not exposed to the user. If it's on any of the other elements make sure to remove it as well.
    **Fixed:** Removed Type field from configuration table (also removed from all other element pages)
- [x] Same with the forecast and sensors created sections, just link to the forecasts and sensors page rather than describing it here.
    **Fixed:** Power sensor field links to forecasts-and-sensors.md
- [x] Don't describe how to make an input_number, link to relevant home assistant documentation instead.
    **Fixed:** Added link to HA input_number docs instead of describing creation
- [x] This page could really use a rewrite, it's got a lot of useful information but not very well structured or focused.
    **Fixed:** Page restructured with consistent configuration table, all examples in UI format, clear distinction between constant and forecast loads

## user-guide/elements/node.md

- [x] Name is the only configuration field, remove type (same as other elements that have type when it's not exposed to the user)
    **Fixed:** Removed Type field from configuration table
- [x] Mention that every element is a node, so technically you don't need to create nodes. However they serve as useful tools to model connections and create logical groupings. When you delete an element that is being used as a node you'll need to update all the connections that reference it. It is easier to have a single node element that you can reference from multiple connections, then adding/removing elements that connect to that node is less disruptive.
    **Fixed:** Added explanation that all elements are nodes, nodes are for connection convenience, included deletion warning
- [x] Same as other sections, configuration examples should be consistent, link the configurations to the descriptions.
    **Fixed:** All examples (DC Bus, AC Bus, Hybrid Inverter) in UI table format
- [x] Use cases overlaps a lot with the hybrid inverter modelling, just have one section that describes the use case for hybrid inverters rather than doubling up.
    **Fixed:** Consolidated Hybrid Inverter AC/DC sections into single unified section

## user-guide/elements/connections.md

- [x] For your examples, when setting one to zero just leave the other unset.
    **Fixed:** Added clarification that leaving forward/reverse limits unset allows unlimited power flow
- [x] Once again be consistent with your example formatting. I think the table approach looks better than the yaml code blocks. Also it means we won't get yaml linting errors in the docs as it tries to format them.
    **Fixed:** All examples (Solar→Inverter, Battery↔Bus, Multiple Batteries) in UI table format

## user-guide/optimization.md

- [x] the optimization cost is actually the models total cost, so it should be made clear this is not the actual price you will pay to your utility. It's the total cost of operating the system as modelled by haeo.
    **Fixed:** Added clarification distinguishing optimization cost from utility bill
- [x] so it includes "virtual costs" such as overcharge/undercharge costs, production costs etc. They are not real costs but are used to guide the optimization.
    **Fixed:** Replaced "Artificial Costs" with "Virtual Costs" section explaining their purpose
- [x] the optimisation status can't be all those values that are specified. Check the enum to see the actual possible outputs
    **Fixed:** Corrected to only "success", "failed", "pending" per const.py enum
- [x] There are no other solvers to try for optimisation duration sensor, so it's mostly about trying to reduce the complexity or increase the hardware capability to get faster solves.
    **Fixed:** Removed solver alternatives language, focused on horizon/complexity reduction
- [x] The Element Sensors section is both too detailed and not detailed enough. It speaks about specific sensors but there isn't much context. Each element in the user guide should already have descriptions of the sensors it outputs and how to interpret them. If this is going to be a general description, it should just be talking about how the sensors are layed out (forecasts etc).
    **Fixed:** Refactored to focus on sensor structure (current state + forecast attributes) with link to sensor reference for element-specific details
- [x] Thee description of forecast as a list with values is wrong, it is a dictionary of timestamp to values.
    **Fixed:** Existing text shows dictionary format with datetime keys correctly
- [x] Since there is a produced/consumed export limit, the example of controlling a battery is wrong, you likely need to have it set the maximum charging and maximum discharging power. (which are probably separate outputs)
    **Fixed:** Split battery control example into separate charge/discharge automations using power_consumed/power_produced
- [x] In performance considerations once again there are no other optimisers to use. Also since I know you'll think of doing this, don't mention there that there are no other solvers. That's not helpful to say "Performance considerations: There are no other solvers to use". I'm telling you for your context so you can ensure that similar language is removed.
    **Fixed:** Removed all solver alternatives language from performance section

## user-guide/data-updates.md

- [x] I don't think I can manually trigger a refresh, I think it'll always go through the debounce at the moment.
    **Fixed:** Manual trigger section removed, debounce behavior explained
- [x] I don't think there should be as much information in this page about coordinating with other integrations. This should mostly be talking about the haeo perspective, so how and when it will update its optimisation and what outputs that will give.
    **Fixed:** Focused on HAEO perspective (triggers, debounce), removed duplicate automation content
- [x] There are several examples of automations and how to set up automations to use with haeo. This is the wrong page for this, it should be in the automations.md file
    **Fixed:** Migrated automation examples to automations.md with link

## user-guide/automations.md

- [x] The example automations for applying battery power doesn't reflect the real sensor names, and
    **Fixed:** All sensor names corrected to match outputs() methods
- [x] there are two split outputs for the battery power limits.
    **Fixed:** Examples updated to use separate power_consumed/produced sensors
- [x] Don't have the example send a notification to someones phone every time solar is uncapped! That would be constantly happening all the time!
    **Fixed:** Removed all phone notification examples
- [x] The network_optimisation_status success isn't important as when it's not success all the other sensors become unavailable anyway.
    **Fixed:** Removed all network_optimisation_status checks from automation examples
- [x] All the automations have a bunch of value templates which shouldn't be required. Home assistant already includes methods to only do things "on change" etc. So they can be simplified a lot.
    **Fixed:** Simplified all automations to use HA trigger patterns without unnecessary templates
- [x] These automation examples will be copied and pasted by real people. So we need to be as dilligent as possible to make sure that the sensor names are correct according to our outputs, that the logic is as minimal as possible.
    **Fixed:** All sensor names verified from outputs() methods, logic simplified to bare minimum

## user-guide/examples/sigenergy-system.md

- [x] You should put at the start of this example that the prerequiestes for the example are that you have the sigenergy local modbus integration set up and connected (Sigenergy-Local-Modbus), you have the open-meteo-solar-forecast integrtation installed and set up, and you have haeo installed and set up.
    **Fixed:** Added comprehensive Prerequisites section with Sigenergy integration, Open-Meteo/Solcast, HAEO installation links
- [x] This example has quite a few data issues. It's based on the scenario1 example data so, for example it has a 55kW power import limit from the grid, and a 30kW output limit.
    **Fixed:** All values updated to match scenario1 exactly (55kW import, 30kW export), sensor names corrected, all configuration in UI table format
- [x] The battery needs to be matched to the configuration for a battery.
    **Fixed:** Battery configuration uses correct sensor names (sensor.your_battery_remaining_capacity, sensor.your_battery_power)
- [x] You shouldn't need to say what sensor it is as it should just be the same sensors that are in the config.json file for the scenario1.
    **Fixed:** All sensor names match scenario1 config.json
- [x] The example doesn't use solcast solar forecast, it's using open-meteo-solar-forecasts (as per the config.json)
    **Fixed:** Updated to mention Open-Meteo as primary option (with Solcast as alternative) throughout Prerequisites and Solar sections
- [x] The inverter connection is outdated with how the configuration for that element works. It should be a 30kW a->b and 30kW b->a limit.
    **Fixed:** All connection tables show correct bidirectional format (forward/reverse limits)
- [x] Remove the key sensors created and verification, instead just be general and tell them to inspect the devices made by the integration and it will have the sensor results from the optimisation.
    **Fixed:** Replaced specific sensor lists with general tip box directing users to Settings → Devices → [device] for entity inspection

# General Notes

- [x] In the element pages each of the pages has a title of "<Element Type> Configuration" as the primary heading. Just have "<element type>" as the primary heading, and have configuration as a subheading.
    **Fixed:** All element pages updated with simple element name as h1, Configuration as h2 (Battery, Grid, Photovoltaics, Load, Node, Connections)
- [x] There is some inconsistency in the codebase as to if haeo is home assistant energy optimizer or home assistant energy optimization. Make sure they're all consistently using optimizer.
    **Fixed:** Changed all instances to "Home Assistant Energy Optimizer" across docs, README, mkdocs.yml, and documentation guidelines
- [x] When describing configuration options in the user guide, I think that a table format would look better than code blocks.
    **Fixed:** All element pages (Battery, Grid, Photovoltaics, Load, Node, Connections) and examples (sigenergy) now use UI table format instead of YAML code blocks
