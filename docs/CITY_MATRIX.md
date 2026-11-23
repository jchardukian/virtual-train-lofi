# Next 20 destinations: differentiation matrix (proposal)

Written 2026-11-23. Order alternates environments so no two neighbours share a setting.
Each row needs its own opening scene, far strip, ground plane and near foreground. "V1" = the four built cities.

| # | Destination | Setting / terrain | Architecture | Season · time · weather | Ground and near foreground | Signature landmarks | Music mood |
|---|---|---|---|---|---|---|---|
| V1 | Chicago | river city | Chicago School, Marina City | autumn · golden hour | river, riverwalk trees | Marina City, bascule bridges, Willis Tower | warm |
| V1 | Denver | plains city to mountains | brick LoDo, glass towers | autumn · cool morning | prairie, foothills | Union Station, Capitol, Front Range | warm, airy |
| V1 | Paris | river city | Haussmann, zinc roofs | autumn · rose dusk | Seine quay, plane trees | Eiffel Tower, Notre-Dame, Sacré-Cœur | soft, jazzy |
| V1 | Tokyo | dense metropolis | towers, small houses | autumn · overcast day | canal wall, ginkgo | Skytree, Tokyo Tower, Senso-ji | gentle |
| 5 | New York City | elevated line over dense streets | brownstones, art deco towers | winter · blue-lit evening, snow on ledges | rooftops, water tanks, fire escapes | Empire State, Chrysler, Brooklyn Bridge, Queensboro Bridge | night jazz-hop |
| 6 | Swiss Alps (journey) | alpine valley | chalets, stone churches | winter · bright morning, fresh snow | snowfield, pines, wooden fences | Matterhorn, viaduct, lake | crisp, bells |
| 7 | Kyoto | old city and forest edge | wooden machiya, temples | late autumn · golden afternoon | maple slopes, moss, stone walls | Kinkaku-ji, Fushimi Inari gates, bamboo grove, Yasaka pagoda | soft koto-hop |
| 8 | San Francisco | hills and bay | Victorian row houses | spring · fog lifting | hills, cable-car street, bay water | Golden Gate, Painted Ladies, Transamerica | breezy |
| 9 | Amsterdam | canals and polder | gabled canal houses | spring · tulip fields, clouds | canals, bicycles, tulip rows | canal houses, windmills, Rijksmuseum | playful |
| 10 | Cairo and the Nile | desert river city | domes, minarets | summer · hot haze, sunset | sand, palms, felucca river | Pyramids of Giza, Sphinx, Cairo Tower | warm, oud |
| 11 | Edinburgh | volcanic old town | dark stone tenements | late summer · drizzle then sun | moorland, stone walls | Edinburgh Castle, Arthur's Seat, Forth Bridge | wistful |
| 12 | Rio de Janeiro | coast and mountains | colourful hillside houses | summer · bright midday | beach, palms, rainforest slope | Christ the Redeemer, Sugarloaf, Copacabana | bossa-hop |
| 13 | Reykjavik and coast | volcanic coast | small coloured houses | winter · aurora night | black sand, lava fields, moss | Hallgrímskirkja, Harpa, waterfalls | ambient, slow |
| 14 | Venice and lagoon | lagoon city | Gothic palazzi | winter · misty morning | lagoon, gondolas, bridges | St Mark's, Rialto, Grand Canal | romantic |
| 15 | Marrakech and Atlas | desert city to mountains | red walls, riads | spring · warm late afternoon | palm groves, red earth | Koutoubia, Atlas peaks, souks | warm percussion |
| 16 | Hong Kong | harbour metropolis | dense towers, neon signs (no readable text) | summer · humid night | harbour, ferries, hillside | Victoria Harbour, Star Ferry, the Peak | city night |
| 17 | Lake Bled and Ljubljana | lakes and castles | Baroque, castle on cliff | autumn · lake mist | lake, island, forest | Bled island church, castle, dragon bridge | calm |
| 18 | Sydney | harbour city | sandstone and glass | summer · bright blue day | harbour, beaches, gum trees | Opera House, Harbour Bridge | sunny |
| 19 | New Orleans | river and swamp | balconied Creole houses | spring · warm evening | bayou, live oaks, Spanish moss | French Quarter, streetcar, Mississippi | brass-tinged |
| 20 | Santorini and Greek islands | cliff island coast | white cubes, blue domes | summer · sunset | cliffs, sea, olive trees | Oia domes, windmills, caldera | Mediterranean |
| 21 | Banff and Rockies | lake and peaks | timber lodges | winter · clear cold dawn | frozen lake, conifers | Moraine Lake, Banff Springs Hotel | crisp |
| 22 | Istanbul | strait city | domes and minarets | autumn · golden afternoon | Bosphorus water, ferries | Hagia Sophia, Blue Mosque, Galata Tower | warm |
| 23 | Mexico City | high valley city | colonial, colourful | spring · jacaranda purple | trajinera canals, jacaranda | Palacio de Bellas Artes, Angel of Independence, Xochimilco | festive soft |
| 24 | Seoul | river city and mountains | palaces and towers | winter · snowy dusk | Han River, palace walls | Gyeongbokgung, N Seoul Tower | gentle |

## What existing art can and cannot do (measured with the similarity gate)

`pipeline/similarity_gate.py` run on the V1 cities: Tokyo fails against Denver and Paris because all
three use the same near embankment, and Tokyo shares Denver's prairie strip. Middle-of-video frames of
Chicago, Denver and Tokyo hash close together (distances about 20 to 30 of 256), from the shared tree
line and lawn. That confirms the owner's judgement numerically.

Built only from existing art, a new city would reuse those same ground and foreground strips, so it would
fail the gate by construction: Swiss Alps would be Denver's mountains, Kyoto would be Tokyo's pieces,
and there is no New York art at all. A no-spend preview would not be genuinely distinct, so I have not
built one.

## Cost per distinct city (image generation only, at the verified 0.178 USD per high-quality image)

| Item | Images |
|---|---|
| Opening scene plate (city-specific first 5 to 10 seconds) | 1 |
| Landmark sheet | 1 |
| Local architecture sheet | 1 |
| Far strip (skyline or terrain) and ground plane | 1 |
| Near foreground strip (the train's own trackside) | 1 |
| Sky variant when season or time of day differs | 0 or 1 |
| **Total** | **5 to 6 images, about 0.89 to 1.07 USD** |

Plus rejects. The owner's 1 USD per city target holds at five images; six slightly exceeds it.
