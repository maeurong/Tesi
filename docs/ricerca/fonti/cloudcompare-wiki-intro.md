## History

CloudCompare is a 3D point cloud (and triangular mesh) editing and processing software.

Originally, it has been designed to perform direct comparison between dense 3D point clouds. It relies on a specific [octree](/doc/wiki/index.php/Octree "Octree") structure that enables great performances <sup>1</sup> when performing this kind of task. Moreover, as most point clouds were acquired by terrestrial [laser scanners](https://en.wikipedia.org/wiki/Laser_scanning), CloudCompare was meant to deal with huge point clouds on a standard laptop - typically more than 10 million points (in 2005!). Soon after, comparison between a point cloud and a triangular mesh has been supported (see below). Afterwards, many other point cloud processing algorithms have followed (registration, resampling, color/normal vectors/scalar fields management, statistics computation, sensor management, interactive or automatic segmentation, etc.) as well as display enhancement tools (custom color ramps, color & normal vectors handling, calibrated pictures handling, OpenGL shaders, plugins, etc.).

| ![](/doc/wiki/images/9/98/Comp_cloud_mesh.jpg) |
| --- |
| (1) *for instance it took about 10 s. to compute the distances of 3 million points to a 14.000 triangles mesh on a laptop with dual-core processor* |

## Philosophy

## Point cloud Vs Mesh

Regarding its particular history, CloudCompare considers almost all 3D entities as [point clouds](/doc/wiki/index.php/Entities "Entities"). Typically, a triangular mesh is only a point cloud (the mesh vertices) with an associated topology (triplets of 'connected' points corresponding to each triangle). This explains that meshes have always either a point cloud named 'vertices' as sibling or parent (depending on the way they have been loaded or generated). And while CloudCompare will let the user apply some tools directly on a mesh structure (i.e. triangles), some tools can only be applied to the mesh vertices. It may be a bit disturbing at first, but we don't want the user to ignore this: **CloudCompare is mainly a point cloud processing software**.

Of course, as CloudCompare is meant to do change detection (e.g. subsidence monitoring) and as a triangular mesh is a very common way to represent a reference shape (e.g. a building), it is very useful and it couldn't be ignored. Nevertheless it remains a "secondary" entity, especially as CloudCompare is able to compare two point clouds directly, without the need to generate an intermediary mesh.

The main reasons for this are:

- meshes are generally very hard to generate properly on real-life scenes, especially when scanned with a laser scanner (noise, variable density, etc.)
- and as ALS/TLS point clouds are generally very dense (and accurate), we already have all the information we need

## Scalar fields

Among all 'features' that can be associated to a point cloud (colors, normals, etc.) one has a particular place in CloudCompare: the *[scalar field](/doc/wiki/index.php/Entities "Entities")*.

A scalar field is simply a set of values (one per point - e.g. the distance of each point to another entity). As each value is associated to a point (or vertex) it is possible to display those values as colors (with custom color ramps) or to apply filters on them (smooth, gradient, etc.), some basic math operations (exp, log, power of 2 or 3, cos, sin, tan, etc.) and of course to segment the cloud relatively to those values (thresholding, local statistical filtering, etc.).

CloudCompare can handle multiple scalar fields on the same cloud. It is even possible to apply simple arithmetic operations (-,+,/,\*) between two scalar fields of a same cloud.

## Some technical considerations

## Portable

CloudCompare is developed in C++. It is currently compiled on Windows, Linux and Mac OS (thanks to [C-make](http://www.cmake.org/)) and for 32bits and 64bits architectures.

## Trade-off between storage and speed

Here are some details about the technical choices that have been made in CloudCompare (mainly to achieve the goal of loading as much points as possible without downgrading too much performances - i.e. a good trade-off between storage and speed):

- all stored values and most of computations are done with [32bits floating-point values](https://en.wikipedia.org/wiki/Single-precision_floating-point_format)
- to prevent any limitation on the size of arrays (as it's hard to get a big contiguous block of memory on Windows 32 bits), we use a custom container that automatically chunks datasets in small blocks (64 Kb per block).
- normal vectors (if any) are compressed on 16 bits (15 bits actually, because of the way [quantization](https://en.wikipedia.org/wiki/Quantization) works)
- the specific [octree](/doc/wiki/index.php/Octree "Octree") structure used in CloudCompare requires constant per-point memory (i.e. 8 bytes per point on a 32 bits OS - with a maximum depth of 10 - and 12 bytes on a 64 bits OS - with a maximum depth of 21!). It is based on a particular quantization of the 3D point coordinates - a kind of [Morton](https://en.wikipedia.org/wiki/Z-order_curve) ordering scheme - where each point position in the octree grid and at any level is represented by a single integer code. We then process those codes to achieve very efficient nearest-neighbors querying operations. However, while this octree structure is very efficient for computing distances for instance, it's not suitable for fast display (Level Of Detail, etc.).

The result of the above choices is that CloudCompare can store about 90 million blank points per gigabyte of memory. If you add RGB colors, normal vectors, a single scalar field and if you need to compute the octree, you can load up to 32 million points per gigabyte.

On a 64 bits OS you can load as many points as you want (*well, up to 4 billion in fact*). *However, depending on your graphic card capabilities, display and interactivity may be severely downgraded with this many points*;). With a high-end graphic card you can keep a reasonable frame rate with up to 150 million points.

## Recent evolution

While the project has started in 2004 at [EDF R&D](http://research.edf.com/research-and-innovation-44204.html), it has only been released in the public domain around 2009 (under GPL license). As CloudCompare is on open-source project, everyone is free (and welcome) to extend its capabilities. Don't hesitate to ask questions and share your experiences on the [forum](https://www.cloudcompare.org/forum) and to take a look at the [Github](https://github.com/cloudcompare/trunk) source repository.