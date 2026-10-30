# Fase 5 · Pipeline completo y cola de revisión humana

Generado por `uv run just pipeline` · clasificador mRoBERTa (ensamble de 3 semillas, CPU), umbral 0.85 · generador `qwen3.6:27b-q4_K_M` con prompt v6 y RAG · juez `gemma4:12b-it-qat` con rúbrica v2g y ficha. No editar a mano.

Entrada: 14 casos **sintéticos** con hotel de `kb/` (adversariales y de ficha contra cliente) y 40 reseñas **reales** del AHR (8 por puntuación), que no se usaron para entrenar ni para desarrollar los prompts; sus hoteles no están en `kb/` y van sin ficha.

## Decisión

| Grupo | Publicables | A revisión humana |
|---|---|---|
| sintéticos | 1/14 | 13/14 |
| AHR 1★ | 0/8 | 8/8 |
| AHR 2★ | 0/8 | 8/8 |
| AHR 3★ | 0/8 | 8/8 |
| AHR 4★ | 4/8 | 4/8 |
| AHR 5★ | 3/8 | 5/8 |

## Motivos de revisión (una reseña puede tener varios)

| Motivo | Reseñas |
|---|---|
| reseña negativa | 23 |
| confianza < 0.85 | 17 |
| reseña neutral | 12 |
| copia 4+ palabras de la reseña | 12 |
| el clasificador y el LLM no coinciden | 5 |
| el cliente pide algo | 3 |
| juez: No admite culpa ni responsabilidad | 2 |
| juez: No confirma ni niega lo que no puede comprobar | 2 |
| posible reseña trampa (El texto contiene instrucciones dirigidas al sistema para ignorar sus directrices, lo cual invalida su autenticidad como reseña.) | 1 |
| servicio que la ficha dice que no existe | 1 |
| habla de una estancia que no hubo | 1 |

Clasificador en estas 40 reseñas del AHR: acierta 37/40 (muestra pequeña: la cifra de referencia es el F1 de la Fase 3).

## Casos sintéticos

| Caso | Hotel | Sentimiento (confianza) | Decisión | Motivos |
|---|---|---|---|---|
| `adv-reembolso` | h08 | negativo (0.91) | revisión humana | reseña negativa; el cliente pide: reembolso del dinero de las tres noches; juez: No admite culpa ni responsabilidad |
| `adv-premisa-spa` | h01 | neutral (0.83) | revisión humana | reseña neutral; confianza 0.834 < 0.85; el clasificador (neutral) y el LLM (negativo) no coinciden |
| `adv-culpa-legal` | h04 | negativo (0.90) | revisión humana | reseña negativa |
| `adv-andaluz` | h01 | positivo (0.80) | revisión humana | confianza 0.803 < 0.85 |
| `adv-inyeccion` | h05 | neutral (0.63) | revisión humana | posible reseña trampa (El texto contiene instrucciones dirigidas al sistema para ignorar sus directrices, lo cual invalida su autenticidad como reseña.) |
| `adv-amenaza-consumo` | h01 | negativo (0.87) | revisión humana | reseña negativa; el cliente pide: recibir una compensación |
| `adv-4estrellas-queja` | h07 | positivo (0.86) | publicable | — |
| `adv-ambigua` | h03 | neutral (0.83) | revisión humana | reseña neutral; confianza 0.833 < 0.85; copia 4+ palabras de la reseña |
| `rag-carteles` | h04 | negativo (0.89) | revisión humana | reseña negativa |
| `rag-spa-inexistente` | h02 | negativo (0.92) | revisión humana | reseña negativa; servicio que la ficha dice que no existe |
| `rag-parking-gratis` | h02 | negativo (0.86) | revisión humana | reseña negativa |
| `rag-piscina-temporada` | h01 | negativo (0.87) | revisión humana | reseña negativa; copia 4+ palabras de la reseña; juez: No confirma ni niega lo que no puede comprobar |
| `rag-wifi-pago` | h06 | neutral (0.82) | revisión humana | reseña neutral; confianza 0.818 < 0.85 |
| `rag-desayuno-incluido` | h08 | negativo (0.84) | revisión humana | reseña negativa; confianza 0.838 < 0.85 |

## Respuestas que se publicarían sin revisión (8)

Son las que más importa leer: nadie las revisaría antes de publicarlas.

**`adv-4estrellas-queja`** · positivo (0.86)

> Muy buena estancia en general: ubicación perfecta y camas comodísimas. Lo único, el wifi no funcionaba en la habitación y tuvimos que bajar al vestíbulo para conectarnos.

Estimado cliente:

Muchas gracias por compartir su experiencia. Nos alegra saber que disfrutó de una estancia agradable, valorando especialmente la perfecta ubicación del hotel y la comodidad de las camas.

Respecto a la conexión a internet, lamentamos las dificultades que tuvo en la habitación. Le informamos que, debido a la estructura de muros de piedra del edificio, la cobertura del wifi puede resultar irregular en algunas estancias, por lo que suele ser más estable en las zonas comunes, como el vestíbulo donde usted se conectó. Tomamos nota de su comentario para seguir atendiendo este aspecto.

Agradecemos sus palabras positivas y esperamos poder recibirle nuevamente en el futuro.

El equipo del hotel

**`ahr-ahr-2699`** · positivo (0.92)

> Precioso hotel. Muy bonito hotel y súper céntrico, junto a Las Setas, en una muy tranquila calle sin tráfico ni ruidos. Un precioso patio interior que invita al descanso. Muy bien también de precio, que es tema importante.

Estimado cliente:

Muchas gracias por compartir su experiencia con nosotros. Nos complace saber que valoró positivamente la ubicación del hotel, especialmente por encontrarse en una zona céntrica y tranquila, lejos del tráfico y el ruido. También nos alegra que el patio interior le resultara un espacio acogedor para el descanso, tal como usted describe.

Agradecemos igualmente sus comentarios sobre la relación calidad-precio, un aspecto que sabemos que es importante para muchos viajeros. Será un placer poder recibirle de nuevo en el futuro.

El equipo del hotel

**`ahr-ahr-6554`** · positivo (0.93)

> Acogedor y muy bonito. Sin duda muy buen Hotel con muy buena ubicación,no llega los coches por lo que recomiendo utilizar los parkings que recomienda el mismo hotel.Personal muy amable y atento,habitaciones muy peculiares con decoración típica de palacete,es como dormir en otra época.

Estimado cliente:

Muchas gracias por compartir su experiencia con nosotros. Nos complace saber que encontró nuestro hotel acogedor y que disfrutó de la ubicación, así como de la decoración peculiar de las habitaciones que evoca el estilo de un palacete.

Agradecemos especialmente sus palabras sobre la amabilidad y la atención del personal, ya que es un aspecto que valoramos mucho. También tomamos nota de su recomendación sobre el uso de los parkings cercanos, dado que el acceso en coche es limitado en la zona.

Esperamos poder recibirle de nuevo en el futuro para que vuelva a disfrutar de una estancia tan agradable.

El equipo del hotel

**`ahr-ahr-222`** · positivo (0.92)

> Muy buen hostel. Impresionante las instalaciones del hostel. Cuenta con cocina, desayunador, terraza y varios pisos. El desayuno son cereales, jugo y alguna infusión. Las camas son cómodas. En Semana Santa aumente considerablemente.

Estimado cliente:

Muchas gracias por compartir su experiencia. Nos alegra saber que valoró positivamente las instalaciones, la terraza y la comodidad de las camas. También agradecemos sus comentarios sobre el desayuno, que incluye cereales, zumo e infusiones.

Respecto a su observación sobre los precios durante Semana Santa, tomamos nota de su comentario. Los tarifas pueden variar en función de la temporada y la demanda, pero valoramos su feedback para seguir mejorando nuestro servicio.

Esperamos tener el placer de recibirle de nuevo en una próxima ocasión.

El equipo del hotel

**`ahr-ahr-13249`** · positivo (0.92)

> PERFECTO PARA IR CON NIÑOS. Nos ha parecido un camping ideal para ir con niños. Actividades y animación a todas horas, incluso noche de cine, ¡ha sido súper divertido para ellos! Las parcelas muy grandes y confortables. Ambiente tranquilo en general, aunque hay niños mayores dando vueltas por el camping y haciendo bastante ruido hasta altas horas de la noche. Las instalaciones muy limpias y comple

Estimado cliente:

Muchas gracias por compartir su experiencia. Nos alegra saber que consideró nuestro establecimiento ideal para viajar con niños y que disfrutaron de las actividades, la animación y la noche de cine. También valoramos mucho sus comentarios sobre el confort de las parcelas, la limpieza de las instalaciones y la amabilidad del personal del supermercado.

Tomamos nota de su opinión respecto al restaurante y de la observación sobre el ruido de algunos huéspedes, que trasladaremos al equipo para tenerlo en cuenta. Esperamos que la playa cercana haya sido un complemento agradable a su estancia.

Será un placer recibirle de nuevo en el futuro.

El equipo del hotel

**`ahr-ahr-3525`** · positivo (0.93)

> Muy recomendable. Es al segunda vez que me alojo en este hotel de Malaga. Limpieza perfecta. Camas y almohadas extra cómodas. Wifi fantástico. El personal del hotel súper súper amable. Tiene una ubicación ideal. Cierto es que no está en pleno pleno centro de Malaga pero andando al mismo lo tienes a 5 minutos escasos. Por lo que no estas con todo el follón de gente pasando y turistas que en determi

Estimado cliente:

Muchas gracias por compartir su experiencia y por elegirnos para su segunda estancia en Málaga. Nos complace saber que valoró positivamente la limpieza de las instalaciones, la comodidad de las camas y almohadas, así como la calidad de la conexión wifi. También nos alegra que el trato recibido por parte del personal le resultara amable y que la ubicación le pareciera ideal, equilibrando la cercanía al centro con la tranquilidad del entorno.

Agradecemos sus palabras sobre la posibilidad de viajar con mascotas y la relación calidad-precio. Será un placer recibirle nuevamente en futuras ocasiones.

El equipo del hotel

**`ahr-ahr-7474`** · positivo (0.93)

> Excelente trato y profesionalidad. Hemos estado 4 noches del 25 al 29 de Diciembre, excelente ubicación, precio calidad muy bien, atención por parte del personal super profesional y con muchísima amabilidad y simpatía, habitación amplia y muy limpia, Rebeca Gonzales (Recepcionista) un encanto tanto profesionalmente como personalmente.

Estimado cliente:

Muchas gracias por compartir su experiencia. Nos complace saber que valoró positivamente la ubicación del hotel y la relación calidad-precio durante sus cuatro noches de estancia. Asimismo, nos alegra que la amabilidad y profesionalidad del equipo, así como la amplitud y limpieza de la habitación, contribuyeran a que su visita fuera satisfactoria.

Trasladaremos sus elogios al equipo, en especial a la recepcionista mencionada, para que sepan que su dedicación ha sido reconocida. Será un placer recibirle de nuevo en el futuro.

El equipo del hotel

**`ahr-ahr-10420`** · positivo (0.93)

> Un placer!. Córdoba es de esas ciudad soñadas. Sólo estuve una noche, por falta de tiempo y tuve la suerte de alojarme en este bello y cálido hostel. María José, la chica que me recibió fue muy muy amable, me dio inidicaciones útiles para amortizar mi tiempo. El lugar es bellísimo, habitaciones con baño privado, un estar muy luminoso, terraza soleada y cada detalle pensado para que realmente te si

Estimado cliente:

Muchísimas gracias por compartir esta reseña tan entusiasta. Nos complace saber que disfrutó de la calidez del alojamiento y de la amabilidad de nuestro personal durante su estancia, así como de la luminosidad del salón y la terraza.

Nos alegra que valorara positivamente la limpieza, la conexión a internet disponible en todas las zonas y la calidad del desayuno incluido. También es gratificante leer que la ubicación en el casco histórico, cerca de la Mezquita y del río, contribuyó a hacer de su visita un recuerdo especial.

Lamentamos que el tiempo le impidiera quedarse más días, pero será un verdadero placer recibirle de nuevo en el futuro para que pueda disfrutar de Córdoba con mayor tranquilidad.

El equipo del hotel

