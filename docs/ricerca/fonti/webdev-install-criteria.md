Pete LePage

Las Aplicaciones Web Progresivas (PWA) son aplicaciones modernas y de alta calidad construidas con tecnología de Internet. Las PWA ofrecen funciones similares a las de las aplicaciones para iOS/Android/escritorio, son confiables incluso en condiciones inestables de la red y pueden instalarse, lo que facilita que los usuarios las encuentren y las utilicen.

La mayoría de los usuarios están familiarizados con la instalación de aplicaciones y con las ventajas de contar con una experiencia instalada. Las aplicaciones instaladas se encuentran en las superficies de arranque del sistema operativo, como la carpeta de Aplicaciones en Mac OS X, el menú de Inicio en Windows y la pantalla de inicio en Android e iOS. Las aplicaciones instaladas también aparecen en el selector de actividades, en los motores de búsqueda de los dispositivos, como Spotlight, y en las hojas para compartir contenidos.

La mayoría de los navegadores indican al usuario que su Aplicación Web Progresiva (PWA) se puede instalar cuando cumple determinados criterios. Algunos ejemplos de estos indicadores son un botón de instalación en la barra de direcciones o un elemento del menú de instalación en el menú desplegable.

![Captura de pantalla de omnibox con el indicador de instalación visible](https://web.dev/static/articles/install-criteria/image/captura-de-pantalla-de-om-c8d1cf668b8c2_2880.png?hl=es)

Promoción de la instalación proporcionada por el navegador (de escritorio)

![Captura de pantalla para la promoción de instalación proporcionada por el navegador.](https://web.dev/static/articles/install-criteria/image/captura-de-pantalla-para-a3a43236f90d6_2880.png?hl=es)

Promoción de instalación proporcionada por el navegador (para dispositivos móviles)

Además, cuando se cumplen los criterios, muchos navegadores lanzarán un evento `beforeinstallprompt`, lo que le permitirá proporcionar una UX personalizada en la aplicación que activará el flujo de instalación dentro de su aplicación.

## Criterios de instalación

En Chrome, su Aplicación Web Progresiva debe cumplir los siguientes criterios antes de que se active el evento `beforeinstallprompt` y se muestre la promoción de instalación en el navegador:

- La aplicación web aún no está instalada
- Cumple con una heurística de participación del usuario
- Se publica por medio de HTTPS
- Contiene un [manifiesto de la aplicación web](https://web.dev/add-manifest?hl=es) que incluye:
	- `short_name` o `name`
		- `icons`: debe incluir un icono de 192 px y uno de 512 px
		- `start_url`
		- `display`: debe ser de `fullscreen`, `standalone` o `minimal-ui`
		- `prefer_related_applications` no debe estar presente o ser `false`
- Registre a un service worker con un controlador de `fetch`

Otros navegadores tienen criterios similares de instalación, aunque puede haber pequeñas diferencias. Consulte los sitios correspondientes para conocer todos los detalles:

- [Edge](https://docs.microsoft.com/microsoft-edge/progressive-web-apps#requirements)
- [Firefox](https://developer.mozilla.org/docs/Web/Progressive_web_apps/Installable_PWAs)
- [Opera](https://dev.opera.com/articles/installable-web-apps/)