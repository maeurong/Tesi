> [!info] Info
> **Important Update:** JOSS has updated its submission scope requirements, affecting what is eligible for submission and what information is required in your paper. [Read the announcement →](https://blog.joss.theoj.org/2026/01/preparing-joss-for-a-generative-ai-future) • [View updated requirements →](https://joss.readthedocs.io/en/latest/submitting.html#scope-and-significance)

### What exactly do you mean by 'journal'

The Journal of Open Source Software (JOSS) is an academic journal (ISSN 2475-9066) with a formal peer review process that is designed to *improve the quality of the software submitted*. Upon acceptance into JOSS, a Crossref DOI is minted and we list your paper on the JOSS website.

### Don't we have enough journals already?

Perhaps, and in a perfect world we'd rather papers about software weren't necessary but we recognize that for most researchers, papers and not software are the currency of academic research and that citations are required for a good career.

We built this journal because we believe that after you've done the hard work of writing great software, it shouldn't take weeks and months to write a paper about your work.

### You said developer friendly, what do you mean?

We have a simple submission workflow and [extensive documentation](https://joss.readthedocs.io/en/latest/submitting.html) to help you prepare your submission. If your software is already well documented then paper preparation should take no more than an hour.

You can read more about our motivations to build JOSS in our [announcement blog post](http://www.arfon.org/announcing-the-journal-of-open-source-software).

> [!primary] Primary
> [🎉 Volunteer to review for JOSS ⟶](https://reviewers.joss.theoj.org/join)

## Scope & submission requirements

Not all software is eligible to be published in JOSS.

## What we mean by research software

JOSS publishes articles about research software. This definition includes software that: solves complex modeling problems in a scientific context (physics, mathematics, biology, medicine, social science, neuroscience, engineering); supports the functioning of research instruments or the execution of research experiments; extracts knowledge from large data sets; offers a mathematical library, or similar. While useful for many areas of research, pre-trained machine learning models and notebooks are not in-scope for JOSS.

## Scope and significance

JOSS publishes articles about software that has demonstrated clear research impact. Your software should represent a meaningful contribution to the research community rather than being a one-off tool for a single analysis.

We evaluate submissions based on evidence of research impact, intellectual contribution, and good open-source practices. Some factors that reviewers and editors consider include:

- Evidence of research impact: publications or analyses using the software, external adopters or integrations.
- Design thinking: meaningful architectural decisions, trade-offs considered, and conceptual frameworks that capture domain expertise. We value work that builds upon existing software ecosystems rather than reinventing solutions.
- Open development practices: sustained development over time with evidence of collaborative effort, public development history, comprehensive testing, clear documentation, and pathways for community contribution.
- Whether the software is sufficiently useful that it is *likely to be cited* by other researchers in your domain.

In addition, JOSS requires that software should be feature-complete (i.e., no half-baked solutions) and designed for maintainable extension (not one-off modifications of existing tools). "Minor utility" packages, including "thin" API clients, and single-function packages are not acceptable.

Projects developed privately are not eligible until there is a public record of open development: at least six months of public history prior to submission, with evidence of releases, public issues/pull requests. A history of contributions and engagement from individuals beyond the original team, across organisations, is especially welcome, though not essential.

### AI Usage Policy

**Author use:** The use of generative AI is permitted for most aspects of a JOSS submission (e.g., software creation and review, generating documentation, assisting with paper authoring), however all such use must be disclosed in an "AI usage disclosure" statement which includes:

- **Tool use:** The tools/models used (and versions) and where they were used (code, paper text, docs).
- **The nature and scope of assistance:** e.g., code generation, refactoring, test scaffolding, copy-editing, drafting.
- **Confirmation of review:** Authors must assert that human authors reviewed, edited, validated all AI-assisted outputs and made the core design decisions.

AI is not allowed for conversational interactions between authors and editors or reviewers unless it is being used for translation purposes.

Authors remain fully responsible for the accuracy, originality, licensing, and ethical/legal compliance of all submitted materials. Failure to provide a complete and accurate disclosure of AI usage may be considered an ethical breach. Consequences can include desk rejection, mandatory revisions, and post-publication correction or withdrawal. In cases of intentional misrepresentation or non-disclosure, JOSS reserves the right to notify the authors' institutions, funders, and/or relevant professional or scholarly societies in accordance with standard research-integrity practices.

**Reviewer use:** Reviewers may use generative AI tools to assist with non-substantive tasks (e.g., grammar checks of their review text, contextualizing public materials and code snippets) and must disclose this briefly at the end of their review.

- **Accountability:** The reviewer – not the AI – owns the evaluation. All judgements, recommendations, and technical claims must be the reviewer's and verified by them.
- **Human-only judgements:** When reviewing JOSS submissions (code or papers), all evaluative decisions – scoring, accept/reject recommendations, and assessments of originality, novelty, correctness, significance, and policy/ethics compliance – must be made by the human reviewer. AI tools may assist with analysis, but they must not render or determine any verdicts.

### A note on web-based software

Many web-based research tools are out of scope for JOSS due to a lack of modularity and challenges testing and maintaining the code. Web-based tools may be considered 'in scope' for JOSS, provided that they meet one or both of the following criteria: 1) they are built around and expose a 'core library' through a web-based experience (e.g., R/ [Shiny](https://www.rstudio.com/products/shiny/) applications) or 2) the web application demonstrates a high-level of rigor with respect to domain modeling and testing (e.g., adopts and implements a design pattern such as [MVC](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) using a framework such as [Django](https://www.djangoproject.com/)).

## JOSS submissions must:

- Be open source (i.e., have an [OSI-approved license](https://opensource.org/licenses/category)).
- Have an obvious research application.
- Be feature-complete (no half-baked solutions) and be designed for maintainable extension (not one-off modifications).
- Minor 'utility' packages, including 'thin' API clients, and single-function packages are not acceptable.

> [!primary] Primary
> [👀 Full details about the JOSS submission requirements and submission process⟶](https://joss.readthedocs.io/en/latest/submitting.html)

## Editorial Board

##### Warrick Ball (@warrickball)

Associate Editor-in-Chief: Astronomy, Astrophysics, and Space Sciences

University of Birmingham, Birmingham, UK

Research Software Engineer (RSE) at the University of Birmingham since 2023. Everyday user of Fortran and Python; increasingly dabbling in various languages and tools as a part of being an RSE.

##### Matthew Feickert (@matthewfeickert)

Associate Editor-in-Chief: Physics and Engineering

University of Wisconsin-Madison, Madison, WI, USA

Matthew is a research scientist in experimental high energy physics and data science at the [Data Science Institute at the University of Wisconsin-Madison](https://dsi.wisc.edu/). He works as a member of the [ATLAS](https://atlas.cern/discover) collaboration on searches for physics beyond the Standard Model with experiments performed at CERN's Large Hadron Collider (LHC) in Geneva, Switzerland. He also serves on the executive board of the Institute for Research and Innovation in Software for High Energy Physics ([IRIS-HEP](https://iris-hep.org/)) where he is a researcher and the Analysis Systems Area lead.

##### Samuel Forbes (@samhforbes)

Durham University, Durham, UK

Samuel Forbes is an Assistant Professor of Developmental Science at Durham University in the United Kingdom. He specialises in infant cognitive and linguistic development. His research has a particular focus on methods, developing pipelines in eye-tracking, pupillometry and fNIRS.

##### Daniel S. Katz (@danielskatz)

Associate Editor-in-Chief: Computer science, Information Science, and Mathematics

University of Illinois at Urbana-Champaign, Urbana-Champaign, IL, USA

Works on computer, computational, and data research at [NCSA](http://www.ncsa.illinois.edu/), [CS](http://www.cs.illinois.edu/), [ECE](http://www.ece.illinois.edu/), and the [iSchool](https://www.ischool.illinois.edu/) at [the University of Illinois at Urbana-Champaign](http://illinois.edu/), and has a strong interest in studying common elements of how research is done by people using software and data.

##### Rachel Kurchin (@rkurchin)

Associate Editor-in-Chief: Biomedical Engineering, Biosciences, Chemistry, and Materials

Carnegie Mellon University, Pittsburgh, PA, USA

Rachel is an assistant research professor of Materials Science and Engineering at Carnegie Mellon. She has expertise in first-principles modeling (DFT) of solids, particularly point defects, as well as device-level modeling for energy applications such as photovoltaics and electrochemical systems. Her primary programming language is Julia, but she also works in Python and MATLAB.

##### Kevin M. Moerman (@Kevin-Mattheus-Moerman)

Associate Editor-in-Chief: Biomedical Engineering, Biosciences, Chemistry, and Materials

University of Galway, Galway, Ireland

Assistant Professor in Mechanical Engineering at the University of Galway, Ireland. Senior Member IEEE. Developer for the [COMODO](https://github.com/COMODO-research/Comodo.jl) and [GIBBON](http://www.gibboncode.org/) computational biomechanics projects.

##### Kyle Niemeyer (@kyleniemeyer)

Associate Editor-in-Chief: Physics and Engineering

Oregon State University, Corvallis, OR, USA

Associate Professor of Mechanical Engineering in the [School of Mechanical, Industrial, and Manufacturing Engineering](https://engineering.oregonstate.edu/MIME/) at [Oregon State University](http://oregonstate.edu/). Computational researcher in combustion, fluid dynamics, and chemical kinetics, with an interest in numerical methods and GPU computing strategies.

##### Arfon Smith (@arfon)

Editor-in-Chief

Schmidt Sciences, New York, NY, USA

Senior Fellow @ Schmidt Sciences. Previously Director of Product for @github's Copilot and before that Head of Data Science [@stsci](http://www.stsci.edu/). [Zooniverse co-founder](http://www.zooniverse.org/). Editor-in-chief of the Journal of Open Source Software

##### Kristen Thyng (@kthyng)

Associate Editor-in-Chief: Earth Sciences and Ecology

Axiom Data Science, Portland, OR, USA

MetOcean Data Scientist at Axiom Data Science. Researches coastal ocean dynamics, transport of material in the ocean, and tidal turbines as a renewable energy source.

##### Chris Vernon (@crvernon)

Associate Editor-in-Chief: Data Science, Artificial Intelligence, and Machine Learning

Pacific Northwest National Laboratory, Richland, WA, USA

Chris is a chief data scientist specializing in all things geospatial who drives vision for the development of AI-integrated, open-source software ecosystems. His research at the US DOE's Pacific Northwest National Laboratory focuses on artificial intelligence, machine learning, MultiSector Dynamics, multi-model integration, exploratory modeling, natural language processing, graph theory, geospatial solutions, etc.

## Topic Editors

##### Fruzsina Agocs (@fruzsinaagocs)

Editor: boundary integral equations, PDEs, ODEs, computational physics, astrophysics, cosmology

University of Colorado Boulder, Boulder, CO, USA

Assistant Professor at CU Boulder in Computer Science, with a background in theoretical and computational cosmology and physics. My current research interests include using the boundary integral equation formulation to solve PDEs to high-order accuracy, particularly in complex geometries; the numerical solution of ODEs, with a focus on oscillatory equations; high-order quadrature methods; computational (astro-)physics.

##### Gabriela Alessio Robles (@galessiorob)

Editor: Data Science, Open Source Software

Netflix, Los Gatos, CA, USA

Gabriela is a Staff Data Scientist and Analytics Engineer with deep expertise in evaluation infrastructure, data quality frameworks, and observability for GenAI systems. She has worked across GitHub, Atlassian, and Netflix, and currently leads annotation and telemetry infrastructure for large-scale generative AI pipelines. Her work connects rigorous measurement science, including inter-annotator reliability and LLM-as-a-Judge calibration, with the practical demands of production AI systems. Throughout her career, Gabriela has championed the inclusion of multicultural perspectives in technology, believing that fair and representative data practices are foundational to trustworthy AI.

##### Stefan Appelhoff (@sappelhoff)

Editor: Python, MEG, EEG, iEEG, Psychology, Neuroscience, Cognitive Science

Zander Labs, Berlin, Germany

Senior Biosignal Data Analyst at Zander Labs. Developer and maintainer of open source packages and data standard (e.g., MNE-Python, Brain Imaging Data Structure).

##### Marlin Arnz (@marlinarnz)

Editor: transport, accessibility, energy

TU Berlin, Berlin, Germany

I am a transport and environmental economist with backgrounds in spatial, socio-behavioural, and techno-economic modelling.

##### Jack Atkinson (@jatkinson1000)

Editor: climate, earth science, atmospheric science, numerical modelling, simulation, high-performance computing

University of Cambridge, Cambridge, UK

I am a research software engineer at Institute of Computing for Climate Science at the University of Cambridge. Much of my work is around climate modelling, but touches a range of areas including software design and distribution, high performance computing, and machine learning and coupling. I also develop and deliver teaching resources in these areas. Regular user of Fortran and Python, with frequent use of various other languages.

##### Mojtaba Barzegari (@mbarzegary)

Editor: scientific computing, computational mechanics, computational materials science, finite element, numerical methods, topology optimization, computational electrochemistry, high-performance computing, machine learning

Eindhoven University of Technology, Eindhoven, Netherlands

PostDoc researcher at Eindhoven University of Technology (TU/e) in the field of computational chemical engineering. Before joining TU/e, I did my PhD in computational biomedical engineering at KU Leuven, Belgium.

##### Johanna Bayer (@likeajumprope)

Editor: Neuroscience, neuroimaging, computer science, machine learning

Radboud University Medical Center, Nijmegen, Netherlands

I am a post doctoral Fellow at the Donders Institute for Brain, Cognition and Behaviour and the RadboudUMC in Nijmegen, the Netherlands. I have a background in neuroscience, neuroimaging, computer science, machine learning and psychology/cognitive science. I also have some experience in statistical modelling, (Bayesian statistics, MCMC, Gaussian Processes). My proficiency in programming languages covers Python, Matlab and R and Stan.

##### Juanjo Bazán (@xuanxu)

Editor: Astrophysics, Mathematics, Data Science

Universidad Autónoma de Madrid, Spain

Astrophysics researcher, mathematician and software engineer currently developing chemical evolution models for galaxies. He is currently part of the science operations team at the [European Space Astronomy Centre](https://www.esa.int/About_Us/ESAC). Juanjo has worked as advisor on open source policies and contributed code to many popular libraries like Rails or Astropy. He is member of the founder team of [Consul](http://consuldemocracy.org/), the more widely used open sourced citizen participation software.

##### Sophie Beck (@phibeck)

Editor: electronic structure, materials science, quantum materials, condensed matter, solid-state physics, molecular dynamics, data visualization

TU Wien, Vienna, Austria

Materials scientist at TU Wien in Austria, interested in electronic structure methods, strong electronic correlations and their effects on materials properties. Sophie's research focuses on the application and development of computational methods for realistic modeling of strongly correlated materials.

##### Sebastian Benthall (@sbenthall)

New York University School of Law, New York, NY, USA

Sebastian Benthall is an interdisciplinary researcher working on the economics of privacy and security at NYU School of Law. He received his PhD in Information Management and Systems from the University of California, Berkeley. His research has focused on how privacy and security depends on data flow and digital supply chain networks. More recently, he has become a contributing Research Engineer on Econ-ARK, an open source toolkit for structural modeling of heterogeneous agents.

##### Monica Bobra (@mbobra)

Editor: Data Science, Public Policy, Heliophysics, Space Weather

State of California, Sacramento, CA, USA

Monica Bobra serves as the Principal Data Scientist for the State of California. She previously studied the Sun and space weather at Stanford University and the Harvard-Smithsonian Center for Astrophysics.

##### Frederick Boehm (@fboehm)

Editor: Statistical genetics, reproducible research, systems genetics, statistics, biostatistics

University of Michigan, Ann Arbor, MI, USA

Fred is a biostatistician with research interests in statistical genetics and quantitative trait locus mapping in model organisms. He maintains the qtl2pleio R package. As a postdoctoral researcher at the University of Michigan, he develops statistical methods for genomewide polygenic scores.

##### Sébastien Boisgérault (@boisgera)

Editor: Control theory, robotics, dynamical systems, optimization, Python, software engineering

Mines Paris – PSL, Paris, France

Associate Professor at Mines Paris – PSL university (France). Member of the executive team of the Institute for Digital Transformations, researcher at Center for Robotics, lecturer in Mathematics and Software Engineering for the "Cycle Ingénieur Civil" Mines Paris education program. Specialized research topics: shape optimization and delay-differential systems. Author of open-source software (pandoc for Python, bitstream, pioupiou, etc.) and open educational ressources (control engineering with python, dfferential integral and stochastic calculus, etc.).

##### Augusto Borges (@borgesaugusto)

Editor: Biological physics, Biophysics, Mathematical modeling, Computational physics, Bioinformatics, Mechanobiology, Cell Mechanics

University of Cambridge, Cambridge, UK

I am a biological physicist with a keen interest in mechanobiology and soft matter physics. My research focuses on using mathematical and computational modelling to understand complex biological phenomena. Currently, I am a Postdoctoral Research Associate at the University of Cambridge, where I study how physical forces contribute to tissue dynamics, morphogenesis, and regeneration.

##### Josh Borrow (@JBorrow)

Editor: astronomy, python, visualization

University of Pennsylvania, Philadelphia, PA, USA

I am a Systems Architect at the University of Pennsylvania working on software for the Advanced Simons Observatory.

##### Gabriele Bozzola (@Sbozzolo)

Editor: python, julia, high-performance computing, gpu, numerical relativity, astrophysics, gravitational waves, earth system model, land model, atmospheric model, computational electromagnetics

AWS Center for Quantum Computing, Pasadena, CA, USA

I am an Applied Scientist at the AWS Center for Quantum Computing, where I contribute to the development of palace, a finite-element code for computational electromagnetics. Before joining AWS, I contributed to the CliMA Earth System Model as a Software Engineer. My background is in numerical relativity and computational astrophysics.

##### Jed Brown (@jedbrown)

Editor: Computational Science and Engineering, Geophysics, High-performance Computing

University of Colorado Boulder, Boulder, CO, USA

Associate Professor of Computer Science at the University of Colorado Boulder leading a research group developing scalable algorithms and sustainable software for prediction, inference, and design via high-fidelity and multiscale physically-based models. He is a core developer of [PETSc](https://mcs.anl.gov/petsc/).

##### Tobias Buck (@TobiBu)

Editor: astronomy, computational galaxy formation, machine learning, high performance computing, differentiable programming, JAX

Heidelberg University, Heidelberg, Germany

I am a research group leader at the Interdisciplinary Centre for Scientific Computing at Heidelberg University. My research combines computational astrophysics, machine learning and differentiable programming to study galaxy formation. I am particularly interested in the formation of the Milky Way, its chemical evolution and what small dwarf galaxies can tell us about cosmology.

##### Philip Cardiff (@philipcardiff)

Editor: Computational fluid dynamics, computational solid mechanics, multi-physics, finite volume method, finite element method, numerical methods, machine learning

University College Dublin, Dublin, Ireland

Professor in Computational Mechanics at the School of Mechanical and Materials Engineering, University College Dublin (www.ucd.ie). Interested in novel numerical methods for solving mechanics problems in engineering.

##### Taher Chegini (@cheginit)

Editor: hydrology,python

Purdue University, West Lafayette, IN, USA

I am a postdoc at Purdue University, West Lafayette, Indiana, US, working on large-scale flood modeling and synthetic river bathymetry generation

##### Pi-Yueh Chuang (@piyueh)

Editor: numerical methods, computational fluid dynamics, computational science and engineering

Argonne National Laboratory, Lemont, IL, USA

Postdoctoral Appointee in Mathematics and Computer Science at Argonne National Laboratory. Interested in numerical methods and algorithms, particularly in computational fluid dynamics (CFD), computer-aided engineering (CAE), inverse problems, high-performance computing (HPC), and verification and validation (V&V).

##### Beatriz Costa Gomes (@mooniean)

Editor: neurosciences, computer vision, biomedical engineering, graph neural networks, molecular biology

Microsoft AI, London, UK

My expertise lies in between computer science and biomedical sciences (particularly neuroscience). I work mainly with ML and AI, as I'm a Researcher at Microsoft AI.

##### Patrick Diehl (@diehlpk)

Editor: Computational fracture mechanics, Applied mathematics, C++, asynchronous and task-based programming

Los Alamos National Laboratory, Los Alamos, NM, USA

Patrick is a staff scientists in Applied Computer Science at Los Alamos National Laboratory. His research interests are non-local models, e.g. peridynamics; asynchronous many-task systems; and high performance computing. He is the co-host of the FLOSS for science podcast. Patrick received his PhD from the University of Bonn in Germany.

##### Axel Donath (@adonath)

Editor: astronomy, astrophysics, Python, machine learning, statistics

Center for Astrophysics, Harvard & Smithsonian, Cambridge, MA, USA

I'm a Postdoc researcher at Center for Astrophysics Harvard | Smithsonian. I'm interested in the Galactic population of gamma-ray and X-ray sources. I I also work on statistical methods for analysis of low counts astronomical data and enjoy leading and contributing to open source software projects.

##### Kalyn Dorheim (@kdorheim)

Editor: Global Carbon Cycling, Biogeochemisty, Climate Modeling, Terrestrial Ecosystem Modeling, Disturbance Ecology

Pacific Northwest National Laboratory, Richland, WA, USA

Kalyn is an Earth Scientist at the Pacific Northwest National Laboratory. Her research focuses on developing and using a hierarchy of models to investigate Earth system responses to disturbances and feedbacks. She regularly works with emulators, reduced complexity and/or ML models that emulate computationally expensive models. She has experience with R, Python, and C++.

##### Elizabeth DuPre (@emdupre)

Editor: neuroimaging, machine learning

Stanford University, Stanford, CA, USA

Elizabeth is a cognitive neuroscientist at Stanford University working to model individual brain activity using high-dimensional, naturalistic data sets. She is a strong advocate for the role of community-driven science to improve the generalizability of inferences in human brain mapping.

##### Henrik Finsberg (@finsberg)

Editor: scientific computing, computational physiology, computational biology, finite element, numerical methods, high-performance computing, scientific machine learning

Simula Research Laboratory, Oslo, Norway

I work as a Chief Research Engineer at Simula Research Laboratory in the department of Computational Physiology. My primary role is to develop software and tools for computational modeling of the heart and the brain. I care about reproducibility and open science. I also love teaching and supervising students.

##### Vissarion Fisikopoulos (@vissarion)

Editor: Mathematical Software, Discrete & Computational Geometry, Statistical Computing, Optimization

National and Kapodistrian University of Athens, Athens, Greece

Conducting research on high-dimensional geometric computing, statistics, optimization and their applications. Coordinator of the [GeomScale](https://geomscale.github.io/) project. Affiliated with the [Department of Informatics and Telecommunications](http://www.di.uoa.gr/eng), [NKUA](http://en.uoa.gr/ "uoa"). Scientific collaborator at [Ouragan team, INRIA](https://team.inria.fr/ouragan/team-members/).

##### James Gaboardi (@jGaboardi)

Editor: GIScience, Python, Spatial Optimization, Geocomputation

Oak Ridge National Laboratory, Oak Ridge, TN, USA

James Gaboardi is an Associate Research Scientist in the Geospatial Science and Human Security Division at Oak Ridge National Laboratory. He bridges the gap between pure R&D and research software engineering with a background in scientific software development and spatiotemporal modeling, specifically network-based population and facilities. James also is a core member of the PySAL (Python Spatial Analysis Library) team.

##### William Gearty (@willgearty)

Editor: paleobiology, paleontology, macroecology, phylogenetic comparative methods, data visualization, R, apis, Shiny, spatial statistics, geology, earth sciences

Syracuse University, Syracuse, NY, USA

I am a Postdoctoral Researcher in the Open Source Program Office at Syracuse University, where I promote, teach, and practice open science and open-source software development practices. I develop open-source R packages revolving around data acquisition, cleaning, and visualization in the fields of paleontology, evolutionary biology, and geology. Outside of this I also conduct research in computational paleobiology. I'm specifically interested in the biotic and abiotic constraints and drivers of taxonomic and functional diversity across space and time. To accomplish this, I integrate paleontological and neontological data with advanced computational and statistical tools to investigate the evolution of various biological systems and test hypotheses regarding the constraints and drivers of that evolution.

##### Nikoleta Glynatsi (@Nikoleta-v3)

RIKEN Center for Computational Science, Kobe, Japan

A game theorist, a research software developer and a research scientist in the Discrete Event Simulation research team at the RIKEN Center for Computational Science. Nikoleta's primary research interest is mathematical modelling and its applications to biology, ecology and sociology. She is a fellow of the Software Sustainability Institute, a core developer of the Axelrod-Python library and an advocate for open source.

##### Nick Golding (@goldingn)

Editor: Statistics, Infectious diseases, Ecology, Health data, Reproducibility

University of Western Australia, Perth, Australia

I'm an infectious disease modeller at the University of Western Australia with a focus on vector-borne diseases (e.g. malaria) and epidemic diseases (e.g. COVID-19). My work combines mathematical and statistical modelling, ecology, and public health. I'm the author of the greta R package for general-purpose Bayesian statistical modelling (https://greta-stats.org/). As well as my UWA affiliation, I am an honorary member of staff of: The Kids Research Institute Australia, The University of Melbourne, and Curtin University.

##### Jeff Gostick (@jgostick)

Editor: Materials science, transport phenomena, electrochemistry, image analysis

University of Waterloo, Waterloo, Ontario, Canada

Associate Professor in Chemical Engineering at the University of Waterloo, runs the Porous Materials Engineering & Analysis Lab with a research focus on the transport phenomena in porous materials, especially electrodes. Lead developer of [OpenPNM](http://openpnm.org/) a pore network modeling package, [PoreSpy](http://porespy.org/) a quantitative image analysis toolkit for tomograms.

##### Rohit Goswami (@HaoZeke)

Editor: quantum chemistry, computational chemistry, fortran, optimization, nonlinear optics, photonics, saddle point methods, transition state, nucleation, structure analysis, chemical engineering, C++, Python, NumPy, F2PY, statistics, bayesian statistics, statistical learning, machine learning, finite element methods, tensor methods, thermodynamics

École Polytechnique Fédérale de Lausanne (EPFL), Lausanne, Switzerland

Rohit Goswami is a Postdoctoral Researcher in the Laboratory for Computational Science and Modeling (COSMO) at EPFL, Switzerland, working with Prof. Michele Ceriotti and Dr. Guillaume Fraux on the metatensor ecosystem. He serves as a JOSS Editor (since 2024) and has been a JOSS reviewer since 2018, with expertise in molecular dynamics, high-performance computing, web platforms, finite element methods, optimization, and computer geometry across C++, Rust, Fortran, Julia, JavaScript, Python, and R. Previously, he worked as a Software Engineer II at Quansight Labs (2021-2025) maintaining foundational scientific Python packages like NumPy and F2PY. His technical background includes extensive experience with C++, Python, Fortran, OpenMP/MPI, and scientific simulation tools (ESPResSo, LAMMPS, AiiDA).

##### Matt Graham (@matt-graham)

Editor: computational statistics, Bayesian inference, probabilistic machine learning, numerical modelling, high performance computing, differentiable computing, probabilistic programming

University College London, London, UK

I am a Principal Research Data Scientist in the Centre for Advanced Research Computing at University College London. My research background is in computational statistics and probabilistic machine learning, in particular developing algorithms for performing efficient approximate inference in probabilistic models. I work on a variety of open-source research software projects, particularly in Python, Julia and R, as well as delivering teaching and training on research software development and data science good practice.

##### Matthias Grenié (@Rekyt)

Editor: biodiversity, macroecology, plant functional trait

Université Grenoble Alpes, Grenoble, France

Assistant Professor at the Université Grenoble Alpes and working at Alpine Ecology Lab (LECA) in Grenoble, France in the beautiful French Alps. Interested in, among others things, Macroecology, Functional diversity, Open and Reproducible Science. I'm very interesting in working on the community ecology of plants and the distribution of their functional traits. I also developed and continue developing tools to work with functional trait data. These days, I'm also studying the distribution of medicinal plant species in the French Alps, their relationship with functional trait and their chemodiversity, with the idea of evaluating the impact of harvesting on wild communities.

##### Jayaram Hariharan (@elbeejay)

Editor: Geomorphology, Hydrology

U.S. Department of Defense, USA

Jay is an engineer-turned-geomorphologist-turned-data scientist. He is currently a data scientist with the U.S. Department of Defense.

##### Susan Holmes (@spholmes)

Editor: Statistics, Bioinformatics, Bioconductor, R

Stanford University, Stanford, CA, USA

Professor of Statistics at Stanford, strong supporter of reproducible research, recently stepped off @twitter, now https://fosstodon.org/@SherlockpHolmes Moderator for the stat.AP arXiv. My lab works on developing statistical methods for multi domain data with applications to women's health, immunology and the microbiome.

##### Adam R. Jensen (@AdamRJensen)

Editor: Solar energy, district heating, meteorology, energy storage, electricity generation, GIS, satellite image

Technical University of Denmark, Kgs. Lyngby, Denmark

I'm a scientist at the Technical University of Denmark working with solar energy and have a passion for open science. Pythonista and core developer of the pvlib python package.

##### Mark A. Jensen (@majensen)

Editor: Bioinformatics and Computational Biology, Cancer Genomics, Population and Evolutionary Biology, Databases and Data Architecture, Software Development Lifecycle Management

Frederick National Laboratory for Cancer Research, Frederick, MD, USA

Director of Data Science at the Frederick National Laboratory for Cancer Research, he leads efforts to design, build and maintain scientist-friendly research data systems that integrate clinical and multiomic data across thousands of cancer patient-donors. He is active in open source software development and a supporter of the FAIR (Findable, Accessible, Interoperable, Reusable) movement in scientific data management. A molecular evolutionary biologist by training, he served as an Associate Editor for the Journal of Molecular Evolution from 2008-2013.

##### Prashant Jha (@prashjha)

Editor: Computational Mechanics, Computational Science, Computational Biomechanics, Applied Mathematics

South Dakota School of Mines and Technology, Rapid City, SD, USA

I am an Assistant Professor in the Department of Mechanical Engineering at the South Dakota School of Mines and Technology. Before taking this position, I worked at the University of Portsmouth as a Mechanical Engineering Lecturer (Asst. Prof.). I received a Ph.D. in Civil and Environmental Engineering from Carnegie Mellon University in August 2016. After finishing my Ph.D., I joined the Department of Mathematics at Louisiana State University as a Postdoctoral Fellow and worked on numerical methods and analysis of the peridynamics theory of fracture. I then moved to the Oden Institute at UT Austin to gain experience in the computational mechanics of multiphysics and complex systems. My research interests include solids and granular media mechanics, fracture mechanics, multiphysics and multiscale modeling, and applications of neural networks to engineering problems.

##### Christoph Junghans (@junghans)

Editor: HPC, MD, MolSim

Los Alamos National Laboratory, Los Alamos, NM, USA

I lead the applied computer science group at Los Alamos National Laboratory, where my research focuses on multiscale modeling, computational co-design, and various other interesting topics.

##### Sehrish Kanwal (@skanwal)

Editor: Bioinformatics and Computational Biology, R, reproducibility, genomics and transcriptomics

University of Melbourne, Melbourne, Australia

Sehrish is a bioinformatics scientist at the University of Melbourne Centre for Cancer Research (UMCCR). Her research interests include precision oncology, best practice clinical data (genomics/transcriptomics) analysis and computational bioinformatics methods. She is a strong advocate of gender equity and supporting women in tech and leadership roles in STEM fields. She is a curious researcher, a passionate teacher, and an enthusiastic mentor.

##### Ujjwal Karn (@ujjwalkarn)

Editor: natural language processing, computer vision, responsible AI

Meta AI, Menlo Park, CA, USA

Ujjwal is a Software Engineer at Meta AI, where he focuses on the development of large language and vision models.

##### Vincent Knight (@drvinceknight)

Editor: Mathematics, Applied mathematics, Game Theory, Stochastic processes, Pedagogy, Python

Cardiff University, Cardiff, UK

Vince is a mathematician at Cardiff University. He is a maintainer and contributor to a number of open source software packages and a contributor to the UK python community. His research interests are in the field of game theory and stochastic processes and also has a keen interest in pedagogy. Vince is a fellow of the Software Sustainability Institute and is interested in reproducibility and sustainability of scientific/mathematical research.

##### Olexandr Konovalov (@olexandr-konovalov)

Editor: mathematical software, discrete computational algebra, reproducible research

University of St Andrews, St Andrews, UK

Lecturer in the School of Computer Science at the University of St Andrews. Contributor to the computational algebra system GAP. Instructor/Trainer for The Carpentries. Fellow of the Software Sustainability Institute.

##### Vangelis Kourlitis (@ekourlit)

Editor: Data Science, Machine Learning, Simulation Software, Particle Physics

Argonne National Laboratory, Lemont, IL, USA

A data scientist with a decade of experience at CERN, as part of the ATLAS Experiment. I specialise in scientific software development and advanced data analysis of some of the largest and most complex datasets in the world. My expertise includes data engineering, machine learning and simulation software, complemented by extensive experience authoring and reviewing technical documentation for scientific journals and workshops.

##### Paul La Plante (@plaplant)

Editor: cosmological simulations, radio astronomy, machine learning, data science

University of Nevada, Las Vegas, NV, USA

Paul La Plante is a professor in the Department of Computer Science at the [University of Nevada, Las Vegas](https://www.unlv.edu/). His research interests are primarily in astrophysics and cosmology, where he runs cosmological simulations and develops novel data analysis techniques for processing telescope data. He is also interested in applying machine learning methods to astronomy problems.

##### Johan Larsson (@jolars)

Editor: statistics, data science, optimization, data visualization, machine learning

University of Copenhagen, Copenhagen, Denmark

I am a postdoctoral researchers at the Department of Mathematical Sciences at the University of Copenhagen, where I mainly study high-dimensional statistics, statistical optimization, and regularization. I am also broadly interested in developing software to make mine and others' research accessible and useful.

##### Oskar Laverny (@lrnv)

Editor: Copulas, probability and Statistics, Actuarial sciences, Finance, Stochastic algorithms...

Aix-Marseille University, Marseille, France

Associate professor (Maître de conférence) at the Université Aix-Marseille (Marseille, FR), my research focus on high dimensional statistics and dependence structure estimations, with various fields of applications. Fully qualified actuary, I do have a taste for numerical code and open-source software.

##### Hugo Ledoux (@hugoledoux)

Editor: GIS, 3D geoinformation, computational geometry

Delft University of Technology, Delft, Netherlands

Associate-professor at the [Delft University of Technology](https://www.tudelft.nl/) in the Netherlands. Particularly interested in combining the fields of geographical information systems (GIS) and computational geometry, with an emphasis on 3D modelling.

##### Richard Littauer (@RichardLitt)

Editor: Social sciences, linguistics, data science, machine learning, computer science, informatics, digital humanities, ecology, ornithology, taxonomy, nomenclature

Victoria University of Wellington, Wellington, New Zealand

👋 Hello there. I do a few things: \* I am a PhD student in Computer Science at Te Herenga Waka Victoria University of Wellington. \* I have an MA (Hons) in Linguistics and an MSc in Computational Linguistics. \* I am a researcher in taxonomic nomenclature, ornithology, and entomology. I also work with a lot of community science platforms. \* I am an organizer for CURIOSS, the Community for University and Research Institution Open Source Program Offices (OSPOs). \* I am an organizer of SustainOSS, which holds a space for open source software; I've mostly focused on academic open source and documentation there. \* My main languages professional are Python, JavaScript, and R. You can learn more about me at \[https://burntfen.com\](https://burntfen.com), and see my socials on \[http://richard.social\](http://richard.social).

##### Richard Liu (@rich2355)

Editor: Causal Inference, Deep Learning, Machine Learning, Genetics Data Analysis, Survival Analysis, Semiparametric Theory

NYU Grossman School of Medicine, New York, NY, USA

Richard Liu is a biostatistician working in the Division of Biostatistics, Department of Population Health, NYU Grossman School of Medicine.

##### Owen Lockwood (@lockwo)

Editor: Probabilistic Computing, Machine Learning, Quantum Computing, Ising Models, Python, JAX, C++, Julia

Extropic AI, San Francisco, CA, USA

Senior Research Engineer at Extropic AI

##### Michael Mahoney (@mikemahoney218)

Editor: Forest Ecology, Landscape Ecology, Applied Machine Learning, Spatial Data, Remote Sensing

U.S. Geological Survey, Boston, MA, USA

Mike is a data scientist working on water data delivery with the US Geological Survey. Interests include data access and delivery, modeling spatial data and assessing the results, and new visualization approaches for high-resolution data. He maintains multiple R packages (including [waywiser](https://docs.ropensci.org/waywiser/), [spatialsample](https://spatialsample.tidymodels.org/), and [rsi](https://permian-global-research.github.io/rsi/)) and is an author on [rsample](https://rsample.tidymodels.org/).

##### Shane Maloney (@samaloney)

Editor: heliophysics, space weather

Dublin Institute for Advanced Studies, Dublin, Ireland

Dr Shane Maloney is a Senior Research Fellow at the Dublin Institute for Advanced Studies (DIAS), with over a decade of experience. He is the Principal Investigator of ARCAFF, a Horizon Europe-funded project focused on predicting solar flares using machine learning, and a Co-Investigator on the Spectrometer/Telescope for Imaging X-rays (STIX) instrument aboard the Solar Orbiter (SO) mission. Dr Maloney’s research spans a broad range of topics at the intersection between data analytics and heliospheric physics, with a particular interest in understanding solar activity and its impact on the near-Earth environment or space weather. His work combines fundamental studies of dynamic solar phenomena with more applied goals related to space weather forecasting. Key research themes include particle acceleration, energy storage and release, and large-scale eruptions from the solar atmosphere. He applies advanced data analytics methods, including machine learning techniques, to multi-wavelength solar observations. His research involves simultaneous analysis of data from multiple spacecraft and instruments across a range of wavelengths (radio, EUV, X-ray, and in-situ). Dr Maloney is also a strong advocate for the transition to open, FAIR (Findability, Accessibility, Interoperability, Reuse) and reproducible science.

##### Erick Martins Ratamero (@erickmartins)

Editor: microscopy, data management, image analysis

European Molecular Biology Laboratory (EMBL), Heidelberg, Germany

Data Management Coordinator at EMBL, based in Heidelberg. Open-source data analysis and data management for microscopy data.

##### Brian McFee (@bmcfee)

Editor: Audio, music, signal processing, machine learning, information retrieval, recommender systems

New York University, New York, NY, USA

Brian McFee is Assistant Professor of Music Technology and Data Science New York University. His work lies at the intersection of machine learning and audio analysis. He is an active open source software developer, and the principal maintainer of the [librosa](https://librosa.org/) package for audio analysis.

##### Rocco Meli (@RMeli)

Editor: Computational Chemistry, Computational Biochemistry, Materials Science, Molecular Dynamics, Electronic Structure Theory, Data Science

Swiss National Supercomputing Centre (CSCS), Lugano, Switzerland

Rocco is a Research Software Engineer at the Swiss National Supercomputing Center (CSCS), working on materials science and quantum chemistry applications.

##### Owen Melia (@meliao)

Editor: Partial differential equations, boundary integral equations, inverse problems, computational imaging

Flatiron Institute, New York City, United States of America

I am a Flatiron Research Fellow at the Flatiron Institute Center for Computational Mathematics. I am interested in scientific computing and machine learning for the physical sciences. In particular, my research focuses on developing high-order PDE solvers for inverse and control problems, with applications in cellular biology and scientific imaging.

##### Sarath Menon (@srmnitc)

Editor: Research data management, Computational materials science, Physics, mechanical engineering, molecular dynamics, DFT, Ontologies, Workflows

Max-Planck-Institut für Eisenforschung, Düsseldorf, Germany

Postdoctoral researcher in the department of Computational Materials Design at the [Max-Planck-Institut für Eisenforschung](https://www.mpie.de/). I work on developing software and workflows to enable reproducible research in Materials Science as part of the [NFDI-MatWerk consortium](https://nfdi-matwerk.de/). My research includes the calculation of thermodynamic quantities from the atomistic scale, with methods such as molecular dynamics. Developer of [pyscal](https://pyscal.org/) and [calphy](https://calphy.org/).

##### Tristan Miller (@logological)

Editor: computer science, linguistics, artificial intelligence

University of Manitoba, Winnipeg, Canada

Assistant Professor at the [University of Manitoba Department of Computer Science](https://umanitoba.ca/science/computer-science) and Associate Researcher at the [Austrian Research Institute for Artificial Intelligence](https://www.ofai.at/). My research areas include computational linguistics and language technology. Maintainer of various Free Software projects, including [GPP](https://logological.org/gpp.html).

##### Ivelina Momcheva (@ivastar)

Editor: astronomy, galaxy evolution, high-redshift universe, clusters of galaxies, gravitational lensing, JWST, HST

Max Planck Institute for Astronomy, Heidelberg, Germany

##### Yasmin Mzayek (@ymzayek)

Editor: NLP, AI, Machine learning, statistics, brain imaging, computer vision, Python.

Aix-Marseille University, Marseille, France

I'm a lead developer at FreePro in Marseille, France working on researching and developing AI products in the telecom domain. In the past, I worked as a data scientist at the University of Groningen tackling several projects in computor vision, NLP, and statistical methods and I worked at Inria Saclay as a developer on Nilearn, an open source python package for applying machine learning and statistical methods on brain imaging data. I'm passionate about open source software and the communities around it. I mainly work in Python.

##### Kanishka B. Narayan (@kanishkan91)

Editor: land use change, earth system science, food systems, macroeconomics, integrated assessment modelling

Pacific Northwest National Laboratory, Richland, WA, USA

I'm a Computational Scientist with the Pacific Northwest National Lab in Washington DC, USA. I have experience developing scientific software related to land use change, food and agrosystems and energy systems. The core languages I have experience with include R, python, C and C++.

##### Lorena Pantano (@lpantano)

Editor: translational genomic,Small RNAseq, RNAseq, miRNA, isomiRs, visualization, genomics, transcriptomic, non-codingRNA, data integration and visualization, genomic platforms, oncology, neurodegeneration

Harvard T.H. Chan School of Public Health, Boston, MA, USA

Lorena Pantano is the Director of Bioinformatics Platform at Harvard Chan Bioinformatics Core, she is focused on genomic regulation and data integration/visualization, and has 13 years of experience in biological data analysis and contributing to novel algorithms to improve the quantification and visualization of genomic data.

##### AHM Mahfuzur Rahman (@mahfuz05062)

Editor: Bioinformatics, Computer and/or Information Science, Machine Learning & Data Science

Lowe's Home Centers, Minneapolis, MN, USA

I am Mahfuzur Rahman, a Senior Machine Learning Engineer at Lowe's Home Centers. I am based in Minneapolis, Minnesota in the USA. I study, evaluate, and productionalize Large Language Model (LLM) based RAG systems at Lowe's. I have a Ph.D. from the University of Minnesota in Computer Science, focusing on Computational Biology and Bioinformatics. I am equipped to edit works in Machine Learning, MLOps, Software Engineering, and Bioinformatics.

##### Blake Rayfield (@bkrayfield)

University of North Florida, Jacksonville, FL, USA

Blake Rayfield is an Assistant Professor of Finance and FinTech at the University of North Florida’s Coggin College of Business. His research interests span corporate finance, investments, data science, and applied mathematics. Learn more about his work \[here\](blakerayfield.com).

##### Julia Romanowska (@jromanowska)

Editor: bioinformatics, epidemiology, genetic epidemiology, open science, visualization, epigenetics, education

University of Bergen, Bergen, Norway

I am a bioinformatician and data analyst working at Univ.of Bergen, Norway. I've been working with various topics within biostatistics, genetic and epigenetic epidemiology, and bioinformatics. I am passionate about open science and data visualization. I like teaching and I am one of the co-founders of R-Ladies Bergen.

##### Kelly Rowland (@kellyrowland)

Editor: high-performance computing, nuclear engineering, bioinformatics

Lawrence Berkeley National Laboratory, Berkeley, CA, USA

Kelly L. Rowland is a Computer Systems Engineer in the User Engagement Group at [NERSC](https://www.nersc.gov/) at [LBNL](https://www.lbl.gov/). She obtained her Ph.D. in Nuclear Engineering with a Designated Emphasis in Computational Science and Engineering from the University of California, Berkeley.

##### Neea Rusch (@nkrusch)

Editor: computer science, programming languages, program analysis, verification

Uppsala University, Uppsala, Sweden

I am postdoctoral researcher in computer science. My research interests include programming languages; especially program analysis and verification. I am an open source software enthusiast and a distinguished reviewer of research software artifacts.

##### Anjali Sandip (@AnjaliSandip)

Editor: Fluid flow, Ice sheets/ocean modeling, Finite Element Method, High Performance Computing

University of North Dakota, Grand Forks, ND, USA

Anjali Sandip is a Senior Lecturer in the Mechanical Engineering Department at the University of North Dakota. Her research interests include applied mechanics, numerical methods, and high-performance computing. Anjali’s PI-led research projects have received support from NSF, DOE, and NVIDIA. Before her current position, she was a post-doctoral researcher at the University of Nebraska, where she developed patient-specific computational models of the superficial femoral artery/ stent interaction to treat peripheral artery disease. Anjali serves as a mentor for both undergraduate and graduate researchers. She is an active member of the International Association of Computational Mechanics (IACM) and has delivered numerous presentations and published journal articles. Anjali has bachelor’s, master’s, and doctoral degrees in mechanical engineering.

##### Mehmet Hakan Satman (@jbytecode)

Editor: Computational statistics, optimization, numerical methods, algorithms, data science

Istanbul University, Istanbul, Turkey

Full time professor, working at Econometrics Department of Istanbul University. Lectures on operations research, optimizations, quantitative techniques in business, and computer programming. Research in computational statistics, optimization, algorithms, and data analysis. Developer and maintainer of many open source projects in several languages including Julia, C, R, Python, Rust, and JVM based ones. Author of four books on R & Julia programming, operations research, and genetic algorithms.

##### Jonny Saunders (@sneakers-the-rat)

Editor: neuroscience, p2p, linked data, behavior, lab automation, distributed systems, computer supported collaborative work

UCLA, Los Angeles, CA, USA

Peer to peer collaborative and social systems, data formats, standards, lab automation with single board computers. Mild experience with analysis, statistical modeling, etc. tooling but not my specialty. I speak python, javascript (and the accursed/beloved frameworks), R, MATLAB, ruby, PHP; roughly in that order. I can read C, Rust, and golang. NO LLM SUBMISSIONS. i will not participate in a submission that is written by, designed for, or involves LLMs in some major capacity. Affiliations: - UCLA, Dept. Neurology. Postdoc. - Institute of Pirate Technology. Information Liberation Technician

##### Fabian Scheipl (@fabian-s)

Editor: Regression Models, Machine Learning, Dimension Reduction

Ludwig-Maximilians-Universität Munich, Munich, Germany

Lecturer at Dept. of Statistics, LMU Munich Researcher at Munich Center of Machine Learning Expertise in supervised learning (statistical modelling, machine learning), Bayesian methods, dimension reduction/representation learning. Research focus on functional data. R developer with multiple CRAN packages.

##### Hauke Schulz (@observingClouds)

Editor: Atmospheric Sciences, Observations (In-situ +Remote), Large Eddy Simulations, Big Data Analysis

Danish Meteorological Institute, Copenhagen, Denmark

As an Atmospheric Scientist at the Danish Meteorological Institute, Hauke is focusing on advancing our understanding of atmospheric convection and improvements of forecasting. His research integrates various methods including ground-based lidar/radar observations, satellite observations, large-eddy simulations, and machine learning techniques.

##### Claudia Solis-Lemus (@crsl4)

Editor: statistics, computer science, data science, bioinformatics

University of Wisconsin-Madison, Madison, WI, USA

I am an associate professor at the Wisconsin Institute for Discovery and the Department of Plant Pathology at the University of Wisconsin-Madison. Originally from Mexico City, I did my Undergraduate degrees in Actuarial Sciences and Applied Mathematics at ITAM. Then, I did a MA in Mathematics and a PhD in Statistics at the University of Wisconsin-Madison. I work to develop statistical models to answer biological questions, balancing biological interpretability, theoretical guarantees, and computational tractability.

##### Charlotte Soneson (@csoneson)

Editor: Bioinformatics, data visualization, transcriptomics, reproducible research

Friedrich Miescher Institute for Biomedical Research, Basel, Switzerland

Research Associate at the Friedrich Miescher Institute for Biomedical Research in Basel, Switzerland, with a research background mainly in development and evaluation of analysis methods for transcriptomics data. Developer and maintainer of several open-source R packages for analysis, quality assessment and interactive visualization of high-throughput biological data.

##### Øystein Sørensen (@osorensen)

Editor: Machine learning, neuroimaging, statistics

University of Oslo, Oslo, Norway

Professor of Biostatistics, Department of Psychology, University of Oslo. Research interests include development of statistical and machine learning methods with applications in cognitive neuroscience. Developer and maintainer of several R packages.

##### Evan Spotte-Smith (@espottesmith)

Editor: computational chemistry, electrochemistry, materials science, networks, data science, scientific automation, scientific databases/ontologies, Python, Julia, C/C++

University College Dublin, Dublin, Ireland

I am an Ad Astra Fellow and Assistant Professor of Digital Chemistry at University College Dublin. I am also an Adjunct Professor of Chemical Engineering at Carnegie Mellon University. I have a background in materials science and electrochemistry, and I develop software related to high-throughput calculations, chemical reaction networks, and machine learning for chemistry. I use computational and data tools to address a range of problems centered around sustainability, from synthesizing new materials for batteries to understanding how catalysts degrade.

##### David Stansby (@dstansby)

Editor

University College London, London, UK

I'm currently a Senior Research Software Engineer at Univesity College London, and run the Human Organ Atlas (https://human-organ-atlas.esrf.fr/). I have a undergraduate degree in Physics, and a PhD in space plasma physics, where I discovered how different chemical elements help us trace and understand the solar wind. Since 2021 I have been a research software engineer full time, writing code for researchers across a wide range of disciplines. For the last two years I have run the Human Organ Atlas, a open bio-imaging resource of huge 3D images of the human body. In parallel I'm also heavily involved in the scientific Python community, primarily as maintainer of Matplotlib, sunpy, and zarr.

##### Marcel Stimberg (@mstimberg)

Editor: python, computational neuroscience, modeling, simulation, visualization

Sorbonne Université, Paris, France

I am a Research (Software) Engineer at Sorbonne University, working on tools for computational neuroscience. My main development work revolves around the Brian simulator, a simulator for biological spiking neural networks. Apart from numerical modeling, I am also very interested in data visualization and, of course, Open Science and Free and Open Source. I am also a certified instructor for Software Carpentry.

##### Fabian-Robert Stöter (@faroit)

Editor: Audio, signal processing for music and speech signals, machine learning, perceptual evaluation, reproducible research, web technologies

AudioShake, Frankfurt, Germany

Research Scientist in Audio-ML. His main research interest is in audio processing for music and speech. He recently also became involved in ecoacoustics and cognitive sciences and is a strong advocate for open and reproducible research. Fabian received his Ph.D. in Electrical Engineering from the University of Erlangen-Nuremberg in Germany.

##### Fei Tao (@Fei-Tao)

Editor: Computational mechanics, Finite element method, Machine learning

Dassault Systèmes, West Lafayette, IN, USA

Fei TAO is a Solution Consultant at Dassault Systèmes. He received his Ph.D. in Aeronautics and Astronautics Engineering from Purdue University, West Lafayette. His research focused on computational mechanics, mechanics of composites, finite element method, and machine learning.

##### George K. Thiruvathukal (@gkthiruvathukal)

Editor: programming languages, computer systems, computational science, digital humanities, parallel and distributed computing, software engineering, machine learning, computer vision, robotics, and interdisciplinary applications

Loyola University Chicago, Chicago, IL, USA

Professor and Chairperson of the Computer Science department at Loyola University Chicago, and visiting computer scientist at the Argonne National Laboratory Leadership Computing Facility. Research interests: programming languages, computer systems, computational science, digital humanities, parallel and distributed computing, software engineering, machine learning, computer vision, robotics, and interdisciplinary applications. Past editor-in-chief of [IEEE Computing in Science and Engineering](https://publications.computer.org/cise/).

##### Romain Thomas (@Romain-Thomas-Shef)

Editor: Astronomy, astrophysics, cosmology, graphical interfaces, stand-alone GUI

University of Sheffield, Sheffield, UK

I am the Head of Research Software Engineering at the University of Sheffield where I promote better recognition and management of research software within academia. Before that, I worked at the European Southern Observatory in Chile as fellow and staff astronomer, leading the development of software for astronomical data quality control.

##### Abhishek Tiwari (@abhishektiwari)

Editor: Network Analysis, Workflow Systems, Data Pipelines, Computational Biology, Computational Chemistry, Systems Biology, Distributed Systems, Cloud Computing, Edge Computing, IoT, NLP/ML Systems, Security and Privacy

Australian Computer Society, Sydney, Australia

As a researcher, I am trained on Computational Biology, Computational Chemistry, and Systems Biology problems. I am interested in editing articles utilising network analysis (temporal, spatial, bayesian/probabilistic, markov chains, transformation, visualisation), workflow systems, and data pipelines (streaming, batch, DAG processing model) to these domains. My current expertise lies in large-scale distributed systems, cloud computing, edge computing, IoT, NLP/ML systems with an emphasis on security, privacy, trust, and ML safety so I am open to editing articles related to these themes.

##### Ana Trisovic (@atrisovic)

Editor: reproducibility, workflows, data repositories, research software, machine learning, software citation, open science

Massachusetts Institute of Technology, Cambridge, MA, USA

Research Scientist at MIT. Her work focuses on science of science, research reproducibility, bibliometrics, big data workflows, and research data and software sharing and preservation. Before this role, she was a postdoctoral scholar at Harvard University and University of Chicago. She completed her Ph.D. from the University of Cambridge and CERN in 2018.

##### Adam Tyson (@adamltyson)

Editor: Neuroscience, microscopy, image analysis, Python

Sainsbury Wellcome Centre, University College London, London, UK

Adam is Head Research Engineer at the Sainsbury Wellcome Centre & Gatsby Computational Neuroscience Unit at UCL. He leads the Neuroinformatics Unit, a research software engineering group building tools for neuroscience and machine learning. He also co-founded the BrainGlobe computational neuroanatomy initiative.

##### Adithi R Upadhya (@adithirgis)

Editor: Shiny, Geospatial data analysis, Statistics, Data visualisation

University of Liverpool, Liverpool, UK

Adithi is a Geospatial & Data Science Consultant, R Developer, and an Environmental Data Enthusiast who currently lives in Bengaluru, India, working remotely with the University of Liverpool. Her work revolves around using data to tell meaningful stories about the environment - especially air quality, geospatial data, and public health. She is passionate about working with the open-source community, which has played a key role in helping her develop her programming skills.

##### Anastassia Vybornova (@anastassiavybornova)

Editor: geospatial data science, urban data science, sustainable transportation, network science

IT University of Copenhagen, Copenhagen, Denmark

Postdoc @ University of Copenhagen & IT University of Copenhagen

##### Andrew Walker (@andreww)

Editor: geophysics, mineralogy, planetary science, atomic scale simulation

University of Oxford, Oxford, UK

I am an Associate Professor and Senior Research Fellow in the Department of Earth Sciences at the University of Oxford. My research involves the cross over between the behaviour of the Earth's deep interior and the use of computational modelling at a wide range of scales. I've built and maintain software packages (in Python, Fortran, Matlab and Perl), and teach programming and software development to undergraduates, graduate students and research staff.

##### Yuanqing Wang (@yuanqing-wang)

Editor: machine learning, molecular modeling, graph learning

New York University, New York, NY, USA

Independent fellow @ NYU

##### Rachel Wegener (@rwegener2)

Editor: python, earth science, oceanography, atmospheric science, geospatial software, gis, hydrology, water quality

Bay Area Environmental Research Institute, Petaluma, CA, USA

Rachel is an oceanographer and a cloud engineer interested in developing software tools to enable earth sciences. She is currently working as the cloud infrastructure and coding education lead for the NASA Student Airborne Research Program. Areas of particular interest for Rachel include cloud native file formats and computer science education for earth science researchers.

##### Britta Westner (@britta-wstnr)

Editor: neuroscience, electrophysiology, time series analyses, biomedical source reconstruction, machine learning

Radboud University Medical Center, Nijmegen, Netherlands

Britta Westner is an assistant professor at the Donders Institute at the Radboudumc Nijmegen, focusing on visual processing as well as the intersection of vision, memory, and language, using electrophysiological methods. Britta is enthusiastic about data analysis methods and is a core developer of MNE-Python, an open source analysis package for neurophysiological data.

##### Lucy Whalley (@lucydot)

Editor: materials science, solid-state physics, computational chemistry, electronic structure

Northumbria University, Newcastle, UK

Associate Professor at Northumbria University (Newcastle upon Tyne, UK), using atomistic modelling to study materials for renewable energy technologies. Developing software for pre- and post-processing large-scale electronic-structure calculations and spreading the "better software, better research" message as a fellow of the Software Sustainability Institute. Happy to edit papers in the following fields: materials science, quantum chemistry, electronic structure, solid state physics, thermodynamics, RSE tooling.

##### Ethan White (@ethanwhite)

Editor: ecology, computer vision, time-series modeling, ecological forecasting, python, R, biodiversity

University of Florida, Gainesville, FL, USA

I am a Professor in the Department of Wildlife Ecology and Conservation at the University of Florida, where I am also a member of the UF Artificial Intelligence and Informatics Research Institute. I study data-intensive problems in ecology including ecological forecasting and combining high resolution remote sensing with computer vision models to monitor and understand forests and wildlife at large scales. We focus on real world applications through collaborations with multiple federal agencies and the development of research software in R and Python. Areas that I am particularly qualified to handle include data acquisition and management, object detection/classification in imagery, time-series modeling, species distribution modeling, ecological modeling, and software related to teaching computational skills to others.

##### Erik Whiting (@erik-whiting)

Editor: Bioinformatics, Structural RNA Biology, Health Informatics, Scientific Software Engineering

University of Nebraska-Lincoln, Lincoln, NE, USA

Senior software engineer @ CallRail, Adjunct instructor at Metropolitan Community College, and PhD Student at University of Nebraska - Lincoln (projected graduation 12/2026). His two research focuses are computational methods in RNA secondary structure prediction, and analysis of peripheral artery disease (PAD) genomic data. He has also published research in the field of software engineering and healthcare informatics.

##### Frauke Wiese (@fraukewiese)

Editor: energy system analysis, climate neutrality, sustainability (especially of energy systems), sufficiency

Europa-Universität Flensburg, Flensburg, Germany

Associate professor for the transition of energy systems at the Europa-Universität Flensburg. Her junior research groups focuses on pathways to climate neutral and sustainable energy systems with a foucs on sufficiency, thus an absolute reduction of energy demand. Different energy and sector models support her research for reaching sustainable energy, building, industry and transport sectors.

##### Fangzhou Xie (@fangzhou-xie)

Editor: Optimal Transport, Machine Learning, Econometrics, Health Services, R/C++/CUDA, Open Source Software

Rutgers University, New Brunswick, NJ, USA

PhD Candidate in Economics at Rutgers University. Associate Editor at JOSS and Software Impacts. Author and maintainer of \`rethnicity\` package, widely used for predicting race/ethnicity from names in empirical social science research. Experise in R/C++/CUDA for applications of machine learning models in social sciences.

##### Wentao Ye (@yewentao256)

Editor: GPU computing, CUDA, GPU kernels, high-performance computing, performance optimization, LLM inference, LLM training, quantization, distributed systems, PyTorch

Red Hat, Boston, MA, USA

Machine Learning Engineer @ Redhat Open-source contributor specializing in GPU kernels and large-scale LLM training/inference. vLLM maintainer and code owner for quantization, batch-invariant and CUDA kernels, with a track record of end-to-end performance gains, production reliability fixes, deep community leadership, and cross-org collaboration.

##### Mengqi Zhao (@mengqi-z)

Editor: Hydrology and Water Resources, Multisector Dynamics, Data Science, Spatial Analysis, Data Visualization

Pacific Northwest National Laboratory, Richland, WA, USA

Mengqi Zhao is an Earth Scientist at the Pacific Northwest National Laboratory. She is an expert in modeling hydrologic and water resources systems across diverse spatiotemporal scales, and her research emphasizes the broader context surrounding water, including its role in shaping the complex interactions among energy-water-land-climate systems. She is interested in using novel, integrated Multisector Dynamics (MSD) models to understand the global-national-regional impacts of climate and socioeconomic change on energy-water-land systems.

##### Bonan Zhu (@zhubonan)

Editor: electronic structure,density functional theory,high-throughput calculations,computational materials discovery,crystal structure prediction,energy materials,defects,cluster expansion

Beijing Institute of Technology, Beijing, China

Computational material scientist working on material discovery using electronic structure theory, crystal structure prediction, high-throughput screening and multiscale modelling toolkits. Expertise in Python/Julia and has some Fortran knowledge. Experienced user of CASTEP, VASP, LAMMPS, GULP, ase, pymatgen.

## Editors Emeritus

Tania Allard, Mikkel Meyer Andersen, Lorena A Barba, Katy Barnhart, Eloisa Bentivegna, Teon Brooks, Kakia Chatsiou, Jason Clark, Pierre de Buyl, Renata Diaz, julia ferraioli, Martin Fleischmann, Dan Foreman-Mackey, Jarvist Moore Frost, George Githinji, Richard Gowers, Hugo Gruson, Olivia Guest, Roman Valls Guimera, Melissa Gymrek, David Hagan, Alex Hanna, Alice Harpole, Chris Hartgerink, Bita Hasheminezhad, Lindsey Heagy, Christina Hedges, Gracielle Higino, Kathryn Huff, Aoife Hughes, Luiz Irber, Anisha Keshavan, Thomas J. Leeper, Christopher R. Madan, Abigail Cabunoc Mayes, Melissa Weber Mendonça, Lorena Mesa, Antonia Mey, Juan Nunez-Iglesias, Stefan Pfenninger, Viviane Pons, Jack Poulson, Pjotr Prins, Andrew Quinn, Karthik Ram, Kristina Riemer, Amy Roberts, Marie E. Rognes, Ariel Rokem, Will Rowe, David P. Sanders, Jacob Schreiber, Dana Solav, Matthew Sottile, Ben Stabler, Jemma Stachelek, Andrew Stewart, Yuan Tang, Tracy Teal, Tim Tröndle, Leonardo Uieda, Jake Vanderplas, Mauricio Pacha Vargas Sepulveda, Marcos Vital, Bruce E. Wilson, Yo Yehudi

## Publisher

JOSS is published by [Open Journals](https://www.theoj.org/), an online-only publishing collective [founded in 2016](https://www.arfon.org/announcing-the-journal-of-open-source-software) on the principle that rigorous, community-driven academic publishing should be possible without article processing charges or subscription fees. JOSS is a diamond open access journal (free to read, free to publish) and was the first journal published under Open Journals, created to give research software a citable, peer-reviewed home without the administrative overhead that has historically deterred software authors from publishing their work.

## Peer review

Every JOSS submission undergoes full external peer review, conducted by independent reviewers with relevant domain expertise. Both the paper and the software are reviewed: reviewers evaluate the quality, documentation, and design of the software as well as the accuracy and completeness of the paper itself. Reviews take place openly via public GitHub issues in the [JOSS reviews repository](https://github.com/openjournals/joss-reviews), meaning the full review record (all reviewer comments, author responses, and editorial decisions) is permanently and publicly accessible. Full details of what reviewers assess are described in our [reviewer guidelines](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html) and [review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html); see also our [peer-review policy](#ethics) below.

## How JOSS works

JOSS [heavily automates routine editorial work](https://www.arfon.org/chatops-driven-publishing) (PDF compilation, licence checking, DOI registration, Crossref deposit) so that editors can focus on what matters: ensuring reviews are thorough and that authors receive substantive, constructive feedback. Submissions, reviews, and editorial decisions all take place as public GitHub issues. This approach keeps our operating costs low (see our [cost model](https://blog.joss.theoj.org/2019/06/cost-models-for-running-an-online-open-journal)) while ensuring every step of the editorial process is transparent and open by default.

## How our scope has evolved

Since launch, JOSS has refined its scope twice in response to changing conditions in research software. In [2020](https://blog.joss.theoj.org/2020/07/minimum-publishable-unit), we introduced clearer criteria for what constitutes a substantial scholarly contribution, responding to growth in submission volume and the need for consistent editorial standards. In [2026](https://blog.joss.theoj.org/2026/01/preparing-joss-for-a-generative-ai-future), we updated our criteria to focus on human creativity, design thinking, and demonstrable research impact, a necessary response to the emergence of generative AI tools that changed the relationship between effort and code volume.

## Transparency and operations

We publish [full submission and publication analytics](https://www.theoj.org/joss-analytics/joss-submission-analytics.html) and a detailed [breakdown of our running costs](https://blog.joss.theoj.org/2019/06/cost-models-for-running-an-online-open-journal). JOSS is staffed entirely by volunteers drawn from the research software community.

## Fiscal host and publisher address

Open Journals is an online-only publisher and does not maintain a physical office. Open Journals operates under the fiscal sponsorship of [NumFOCUS](https://numfocus.org/), a 501(c)(3) nonprofit organisation that provides legal and financial infrastructure for open-source scientific computing projects. Correspondence requiring a physical address may be directed to NumFOCUS in their capacity as Open Journals' fiscal host:

NumFOCUS, Inc.  
5900 Balcones Drive #22663  
Austin, TX 78731  
United States of America

## Contact JOSS

For editorial enquiries (including questions about submissions, scope, review decisions, or editorial policy) please [email the Open Journals editorial team](mailto:admin@theoj.org) at [admin@theoj.org](mailto:admin@theoj.org). This inbox is monitored by the JOSS Editor-in-Chief, Arfon Smith, and the [Associate Editors-in-Chief](#editorial_board).

For production matters (DOIs, metadata corrections, archiving), these are handled directly in the paper's GitHub review thread. The Open Journals technical team can be reached by tagging [@openjournals/dev](https://github.com/orgs/openjournals/teams/dev) in the relevant thread.

You can also find JOSS at [Bluesky](https://bsky.app/profile/joss-openjournals.bsky.social "joss-openjournals.bsky.social") and [Mastodon](https://fosstodon.org/@JOSS "https://fosstodon.org/@JOSS")

## Code of Conduct

Although spaces may feel informal at times, we want to remind authors and reviewers (and anyone else) that this is a professional space. As such, the JOSS community adheres to a code of conduct adapted from the [Contributor Covenant](http://contributor-covenant.org/) code of conduct.

Authors and reviewers will be required to confirm they have read our [code of conduct](https://github.com/openjournals/joss/blob/master/CODE_OF_CONDUCT.md), and are expected to adhere to it in all JOSS spaces and associated interactions.

## Ethics Guidelines

We also want to remind authors and reviewers (and anyone else) that we expect and require ethical behavior. Some examples are:

- All authors are obliged to provide retractions or corrections of any mistakes of which they become aware.
- Plagiarism (e.g., violation of another author's copyright), for both software and papers, is not allowed.
- Self-plagiarism (repeated publication of the same work) is not allowed.
- Author lists must be correct and complete. All listed authors must have made a contribution to the work, and all significant contributors should be included in the author list.
- Reviews should be accurate and non-fraudulent. Examples of concerns are: Authors should not suggest reviewers who are not real people or have conflicts (see [conflict of interest policy](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html#joss-conflict-of-interest-policy) for details). Reviewers and editors must disclose conflicts. Bribes for authors, reviewers, editors are not permitted.
**Allegations of misconduct**

Allegations of research misconduct associated with a JOSS submission (either during review, or post-publication) are handled by the Open Journals ethics team. Reports should be sent privately to [our editorial team](mailto:admin@theoj.org) at which point the report will be triaged by the Open Journals ethics officer to determine the nature and severity of the case. Options available to the Open Journals ethics officer range from recommending no action to instigating a full investigation by the Open Journals ethics team which may result in researchers' institutions and funders being notified and the JOSS being retracted.

Although JOSS is not yet a member of [COPE](https://publicationethics.org/) (application pending), our processes are modeled on the [COPE guideline procedures for ethics complaints](https://publicationethics.org/files/publication-ethics-editorial-office-cope-flowchart.pdf).

**Complaints process**

Complaints about the conduct or decision making of the JOSS editorial team can be sent to the [Open Journals governance team](mailto:admin@theoj.org).

## JOSS Publication Ethics and Malpractice Statement

**Editorial Board**
- The JOSS editorial board's members are recognized experts in the field. The full names and affiliations of the members are provided on the journal’s website (see [editorial board](https://joss.theoj.org/about#editorial_board)). The individual editors' contact information are provided on that site, via their GitHub pages, and general contact information for the editorial office also on the [journal’s website](https://joss.theoj.org/about#contact).
**Authors and Authors responsibilities**
- JOSS does not charge any fees for manuscript processing and/or publishing materials, as is stated on the [journal's website](https://joss.theoj.org/about#costs).
- Authors are obliged to participate in peer review process, as described in [submission guidelines](https://joss.readthedocs.io/en/latest/submitting.html#review-process).
- All authors have significantly contributed to the research. The submitting author is required to be a [major contributor to the software](https://joss.readthedocs.io/en/latest/submitting.html#submission-requirements) they are submitting and the review process includes a check that *[‘the full list of paper authors seems appropriate and complete?’](https://joss.readthedocs.io/en/latest/review_criteria.html#authorship)*.
- All authors are obliged to provide retractions or corrections of mistakes (see [ethics](https://joss.theoj.org/about#ethics) and [what should my paper contain?](https://joss.readthedocs.io/en/latest/paper.html#what-should-my-paper-contain)).
- JOSS papers are required to have a [list of references](https://joss.readthedocs.io/en/latest/paper.html#what-should-my-paper-contain), and [financial support](https://joss.readthedocs.io/en/latest/paper.html#what-should-my-paper-contain).
- Forbidden to publish same research in more than one journal (see [ethics](https://joss.theoj.org/about#ethics)).
**Peer-review process**
- All of JOSS's content is subjected to external peer-review. JOSS uses an **external peer review** model: reviewers are independent volunteers from the research community, not members of the JOSS editorial team. (See [about](http://joss.theoj.org/about) and [docs](https://joss.readthedocs.io/en/latest/index.html).)
- JOSS peer-review is defined as obtaining advice on individual manuscripts from reviewers [expert in the field](https://joss.readthedocs.io/en/latest/editing.html#finding-reviewers). This advice is public, and is given to both the editor(s) and the author(s), with the aim of pointing out issues the reviewers believe are [insufficiently addressed for publication](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html#guiding-principles).
- The JOSS review process is clearly described on the [journal’s website](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html).
- Judgments should be [objective](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html#guiding-principles).
- JOSS reviewers should ideally have no conflict of interest. In practice, this is not always possible. If a reviewer has a conflict of interest, it must be declared and recorded, and the editors may [choose to waive](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html#joss-conflict-of-interest-policy) it if this is in the best interest of the review process.
- Reviewers should point out [relevant published work](https://joss.readthedocs.io/en/latest/review_criteria.html#an-important-note-about-novel-software-and-citations-of-relevant-work) which is not yet cited.
- JOSS reviews are public and non-anonymous while in progress and post-review, as they take place via GitHub issues in a public repository.
**Publication Ethics**
- All authors are obliged to provide retractions or corrections of any mistakes of which they become aware.
- Plagiarism (e.g., violation of another author's copyright), for both software and papers, is not allowed.
- Self-plagiarism (repeated publication of the same work) is not allowed.
- Author lists must be correct and complete. All listed authors must have made a contribution to the work, and all significant contributors should be included in the author list.
- Reviews should be accurate and non-fraudulent. Examples of concerns are: Authors should not suggest reviewers who are not real people or have conflicts. Reviewers and editors must disclose conflicts. Bribes for authors, reviewers, editors are not permitted.
- Minor fixes are processed by the Editors in Chief (EiCs), and are publicly handled based on requests from the original authors (managed in the GitHub review linked from the paper).
- Major corrections will be reviewed by the EiC and ethics team. If accepted, the paper will be re-published with an editorial note on the GitHub review (linked from the paper page).
- Retractions: EiC team and the ethics team review. If we deem that a retraction is warranted, we will update the paper and leave a retraction notice ([see an example retraction for the linked paper](https://joss.theoj.org/papers/c44313ada36f12eebbaff10eb0888071))
**Copyright and Access**
- JOSS copyright and licensing information is clearly described on the [journal’s website](https://joss.theoj.org/about#content_license).
- The journal and all individual articles are freely available to all readers.
**Archiving**
- JOSS articles, metadata, and reviews are archived with [Portico](https://www.portico.org/).
**Ownership and management**
- Information about the ownership and/or management of a journal is clearly indicated on the journal’s website (see [http://www.theoj.org](http://www.theoj.org/)).
- JOSS and the [Open Journals](http://www.theoj.org/) do not use organizational names that would mislead potential authors and editors about the nature of the journal’s owner.
**Website**
- The JOSS website (see [https://joss.theoj.org](https://joss.theoj.org/) and [https://joss.theoj.org/about](https://joss.theoj.org/about)), including the text that it contains, demonstrates that care has been taken to ensure high ethical and professional standards.
**Publishing schedule**
- JOSS immediately publishes accepted articles; it is not a serial publication.
**Name of journal**
- As far as we know, the journal name (Journal of Open Source Software (JOSS)) is unique and not one that is easily confused with another journal or that might mislead potential authors and readers about the journal’s origin or association with other journals.

## Cost and Sustainability Model

Journal of Open Source Software is an open access journal *committed to running at minimal costs, with zero publication fees ([article processing charges](https://en.wikipedia.org/wiki/Article_processing_charge)) or subscription fees*.

Under the NumFOCUS nonprofit umbrella, JOSS is now eligible to seek grants for sustaining its future. With an entirely volunteer team, JOSS is seeking to sustain its operations via [donations](https://numfocus.org/donate-to-joss) and grants, keeping its low cost of operation and free service for authors.

In the spirit of transparency, below is an outline of our current running costs:

- Annual Crossref [membership](http://www.crossref.org/02publishers/20pub_fees.html): $275 / year
- Annual Portico [membership](https://www.portico.org/join/how-publishers-can-join/): $250 / year
- JOSS paper DOIs: $1 / accepted paper
- JOSS website hosting (Heroku): $19 / month

Assuming a publication rate of 200 papers per year this works out at ~$4.75 per paper ((19\*12) + 200 + 275 + 250) / 200.

A more detailed analysis of our running costs is available [on our blog](http://blog.joss.theoj.org/2019/06/cost-models-for-running-an-online-open-journal).

#### Income

JOSS has an experimental collaboration with [AAS publishing](https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing) where authors submitting to one of the AAS journals can also publish a companion software paper in JOSS, thereby receiving a review of their software. For this service, JOSS receives a small donation from AAS publishing. In 2019, JOSS received $200 as a result of this collaboration.

#### Donate

Donations are one way for JOSS to offset our costs: [![](https://img.shields.io/badge/Donate-to%20JOSS-brightgreen.svg)](https://numfocus.org/donate-to-joss)

## Content Licensing & Open Access

JOSS is a [diamond/platinum open access](https://en.wikipedia.org/wiki/Open_access#Diamond/platinum_OA) journal. Copyright of JOSS papers is retained by submitting authors and accepted papers are subject to a [Creative Commons Attribution 4.0 International License](http://creativecommons.org/licenses/by/4.0/).

Any code snippets included in JOSS papers are subject to the [MIT license](https://opensource.org/licenses/MIT) regardless of the license of the submitted software package under review.

Any use of the JOSS logo is licensed CC BY 4.0. See the `joss/logo` directory in the [digital-assets](https://github.com/openjournals/digital-assets) repository for more information about it.

[![Creative Commons Licence](https://i.creativecommons.org/l/by/4.0/88x31.png)](http://creativecommons.org/licenses/by/4.0/).

![](/assets/cc-logo-6bd73c91b31e18e58c9d77aae34fac59234b70adf38e1d7113532cfdec98ab00.svg)

[Table of Contents](/toc)  
Public user content licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) unless otherwise specified.  
ISSN 2475-9066