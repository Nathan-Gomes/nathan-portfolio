import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowUpRight,
  Award,
  BookOpenCheck,
  Bot,
  BriefcaseBusiness,
  Building2,
  Calendar,
  ChevronRight,
  Cloud,
  Code2,
  Database,
  Download,
  ExternalLink,
  GraduationCap,
  Mail,
  MapPin,
  MonitorSmartphone,
  Phone,
  Rocket,
  Search,
  Server,
  Smartphone,
  Sparkles,
  Target,
  Terminal,
  Zap,
} from 'lucide-react'
import './App.css'

const resumePath = '/Nathan-Gomes-Resume-April-2026.pdf'

type ProjectVisual = 'scraper' | 'copilot' | 'tutor'

type Project = {
  title: string
  eyebrow: string
  summary: string
  stack: string[]
  highlights: string[]
  metric: string
  accent: string
  icon: typeof Search
  visual: ProjectVisual
  deepDive: string
  whyUseful: string
  workflow: string[]
  today: string[]
}

const projects: Project[] = [
  {
    title: 'Indeed Scraper Tool',
    eyebrow: 'Automation for job hunting',
    summary:
      'I built this Python workflow to turn a repetitive job search into structured leads, filters, and follow-up data so applications move faster.',
    stack: ['Python', 'BeautifulSoup', 'JSON', 'Automation'],
    highlights: ['URL collection', 'role filtering', 'export-ready data'],
    metric: 'Job-search ops',
    accent: '#00a878',
    icon: Search,
    visual: 'scraper',
    deepDive:
      'I treated the job hunt like an operations problem. Instead of manually opening dozens of listings, copying links, and losing track of what is worth applying to, the scraper gathers role data into a cleaner structure that can be filtered and reused.',
    whyUseful:
      'In today’s market, speed and organization matter. New grads are often applying across many boards while trying to tailor resumes and avoid duplicate effort. A tool like this helps turn scattered listings into a repeatable pipeline.',
    workflow: ['Collect listings', 'Filter by role signals', 'Export useful leads'],
    today: ['Reduces repetitive browsing', 'Supports faster applications', 'Creates data a person can actually review'],
  },
  {
    title: 'Autofill CoPilot',
    eyebrow: 'Productivity helper',
    summary:
      'I designed this lightweight assistant concept to reduce form friction with practical UX, repeatable inputs, and cleaner daily workflows.',
    stack: ['Swift', 'Xcode', 'macOS', 'UX systems'],
    highlights: ['local-first flow', 'form patterns', 'desktop utility'],
    metric: 'Faster forms',
    accent: '#ff7a1a',
    icon: Bot,
    visual: 'copilot',
    deepDive:
      'I focused Autofill CoPilot on a familiar pain: entering the same personal, academic, and work-history details across forms. The goal is to make repeated inputs easier to manage while keeping the experience simple enough that it feels like a utility, not another platform.',
    whyUseful:
      'Modern work is full of form-heavy workflows: applications, onboarding, internal tools, portals, and admin tasks. A thoughtful autofill assistant can save time while reducing small mistakes that happen when people rush repetitive entry.',
    workflow: ['Store repeatable fields', 'Detect form patterns', 'Fill with user control'],
    today: ['Cuts down admin friction', 'Improves consistency', 'Fits the rise of personal productivity agents'],
  },
  {
    title: 'Mobile Python Tutor',
    eyebrow: 'Duolingo-style learning app',
    summary:
      'I shaped this as a mobile-first learning concept that teaches Python through short lessons, streaks, playful feedback, and practice loops for younger learners and beginners of any age.',
    stack: ['React Native', 'Python', 'Gamification', 'Cloud sync'],
    highlights: ['bite-size lessons', 'progress streaks', 'interactive quizzes'],
    metric: 'Learn by doing',
    accent: '#7c3aed',
    icon: Smartphone,
    visual: 'tutor',
    deepDive:
      'I wanted Mobile Python Tutor to translate programming education into a format that feels familiar to younger learners: short sessions, visual progress, immediate feedback, and small wins. It lowers the intimidation factor around code by making Python feel like a daily practice habit.',
    whyUseful:
      'Coding literacy is becoming a core skill, but many beginner resources still feel built for adults who already know how to learn technical topics. A mobile tutor can meet learners where they are and make programming approachable earlier.',
    workflow: ['Pick a lesson path', 'Solve tiny Python challenges', 'Earn progress and review mistakes'],
    today: ['Makes CS more accessible', 'Encourages daily learning habits', 'Supports school-age digital literacy'],
  },
]

const stack = [
  { label: 'IT Support', detail: 'systems, users, troubleshooting', icon: MonitorSmartphone },
  { label: 'Cloud Infrastructure', detail: 'AWS, Azure, compute, storage', icon: Cloud },
  { label: 'Infrastructure as Code', detail: 'Terraform, CloudFormation', icon: Server },
  { label: 'DevOps Automation', detail: 'CI/CD, AWS Amplify, Bash', icon: Terminal },
  { label: 'Software Development', detail: 'Python, Java, C, React', icon: Code2 },
  { label: 'Data & Databases', detail: 'SQL, data structures, storage', icon: Database },
]

const fieldNotes = [
  'I am a recent Computer Science graduate building practical tools, not just assignments.',
  'I am cloud-curious: learning deployment, hosting, APIs, and the infrastructure behind real products.',
  'My hobbies show up in the work: productivity systems, learning tools, clean interfaces, and tinkering until things feel useful.',
]

const experiences = [
  {
    role: 'IT/Cloud Support Engineer Intern',
    company: 'HCL',
    location: 'Mississauga, ON',
    date: 'May 2024 - August 2024',
    accent: '#2563eb',
    points: [
      'Supported cloud infrastructure deployments across AWS and Microsoft Azure, including compute, storage, networking, and monitoring services.',
      'Assisted with CI/CD workflows, automation, and monitoring to help keep cloud operations reliable.',
      'Implemented Infrastructure as Code with AWS CloudFormation and Terraform to provision and manage resources across environments.',
      'Earned AWS DevOps and HCL cloud certifications while building practical infrastructure knowledge.',
    ],
    tags: ['AWS', 'Azure', 'Terraform', 'CloudFormation', 'CI/CD'],
  },
  {
    role: 'Customer Service Representative',
    company: 'LCBO',
    location: 'Mississauga, ON',
    date: 'May 2023 - August 2023',
    accent: '#00a878',
    points: [
      'Operated point-of-sale systems accurately while handling transactions and cash procedures.',
      'Maintained compliance with Ontario liquor laws and helped create a welcoming retail environment.',
      'Built communication, accountability, and time-management habits that carry into technical teamwork.',
    ],
    tags: ['Customer support', 'POS systems', 'Compliance', 'Communication'],
  },
]

function BackgroundStory() {
  const nodes = Array.from({ length: 7 }, (_, index) => index)

  return (
    <div className="background-story" aria-hidden="true">
      <div className="signal-line line-one"></div>
      <div className="signal-line line-two"></div>
      <div className="signal-ring ring-one"></div>
      <div className="signal-ring ring-two"></div>
      {nodes.map((node) => (
        <span
          className="mesh-node"
          key={node}
          style={{ '--node': node } as React.CSSProperties}
        ></span>
      ))}
    </div>
  )
}

function ProjectMockup({ project }: { project: Project }) {
  if (project.visual === 'scraper') {
    return (
      <div className="project-visual scraper-visual" aria-label="Indeed Scraper Tool interface mockup">
        <div className="browser-frame">
          <div className="browser-dots"><span></span><span></span><span></span></div>
          <div className="search-row">
            <Search size={16} />
            <span>junior developer toronto</span>
          </div>
          <div className="listing-stack">
            {['Cloud Support Intern', 'Junior React Developer', 'Python Automation Analyst'].map((role, index) => (
              <div className="listing-card" key={role}>
                <strong>{role}</strong>
                <span>{index === 0 ? 'AWS basics' : index === 1 ? 'React + TS' : 'Python scripts'}</span>
                <small>{92 - index * 8}% match</small>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (project.visual === 'copilot') {
    return (
      <div className="project-visual copilot-visual" aria-label="Autofill CoPilot desktop app mockup">
        <div className="copilot-window">
          <div className="copilot-sidebar">
            <span className="active-dot"></span>
            <span></span>
            <span></span>
          </div>
          <div className="copilot-form">
            <p>Profile Pack</p>
            <div className="input-line wide"></div>
            <div className="input-line"></div>
            <div className="input-line short"></div>
            <button type="button">Fill selected fields</button>
          </div>
          <div className="copilot-bubble">
            <Bot size={20} />
            <span>3 fields ready</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="project-visual tutor-visual" aria-label="Mobile Python Tutor app mockup">
      <div className="phone-shell">
        <div className="phone-camera"></div>
        <div className="lesson-card">
          <BookOpenCheck size={24} />
          <strong>Loops 101</strong>
          <span>5 min lesson</span>
        </div>
        <div className="code-card">
          <code>for score in scores:</code>
          <code>    print(score)</code>
        </div>
        <div className="answer-row">
          <span>streak 12</span>
          <button type="button">Run</button>
        </div>
      </div>
    </div>
  )
}

function App() {
  const [activeProject, setActiveProject] = useState(0)
  const selectedProject = projects[activeProject]

  const orbitItems = useMemo(
    () => ['React', 'Cloud', 'Python', 'UX', 'Data', 'Mobile'],
    [],
  )

  return (
    <main className="site-shell">
      <BackgroundStory />
      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand-mark" href="#home" aria-label="Nathan Gomes home">
          NG
        </a>
        <div className="nav-links">
          <a href="#projects">Projects</a>
          <a href="#experience">Experience</a>
          <a href="#cloud">Cloud</a>
          <a href={resumePath} target="_blank" rel="noreferrer">Resume</a>
          <a href="#contact">Contact</a>
        </div>
      </nav>

      <section className="hero-section" id="home">
        <div className="hero-copy">
          <motion.p
            className="status-pill"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Sparkles size={16} />
            I&apos;m a recent CS grad turning curiosity into shipped tools
          </motion.p>
          <motion.h1
            initial={{ y: 18 }}
            animate={{ y: 0 }}
            transition={{ delay: 0.08, duration: 0.65 }}
          >
            I&apos;m Nathan Gomes. I build useful software with a maker&apos;s edge.
          </motion.h1>
          <motion.p
            className="hero-lede"
            initial={{ y: 18 }}
            animate={{ y: 0 }}
            transition={{ delay: 0.16, duration: 0.65 }}
          >
            I&apos;m an ambitious Computer Science graduate focused on IT support,
            cloud infrastructure, automation, and software development. I like
            building practical tools that make messy workflows feel simpler.
          </motion.p>
          <motion.div
            className="hero-actions"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.24, duration: 0.65 }}
          >
            <a className="primary-action" href="#projects">
              View top projects <ArrowUpRight size={18} />
            </a>
            <a className="secondary-action" href="#contact">
              Connect <ExternalLink size={18} />
            </a>
            <a className="resume-action" href={resumePath} download>
              Resume <Download size={18} />
            </a>
          </motion.div>
        </div>

        <motion.div
          className="command-center"
          initial={{ opacity: 0, scale: 0.96, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.16, duration: 0.7 }}
          aria-label="Interactive profile summary"
        >
          <div className="terminal-bar">
            <span></span>
            <span></span>
            <span></span>
            <p>nathan/portfolio</p>
          </div>
          <div className="profile-console">
            <div>
              <p className="console-label">Current mode</p>
              <h2>Build. Learn. Ship.</h2>
            </div>
            <Rocket className="console-icon" size={34} />
          </div>
          <div className="orbit-map">
            {orbitItems.map((item, index) => (
              <span
                key={item}
                style={{ '--i': index } as React.CSSProperties}
              >
                {item}
              </span>
            ))}
          </div>
          <div className="mini-metrics">
            <div>
              <strong>3</strong>
              <p>featured builds</p>
            </div>
            <div>
              <strong>6</strong>
              <p>core tools</p>
            </div>
            <div>
              <strong>AWS</strong>
              <p>Amplify hosted</p>
            </div>
          </div>
        </motion.div>
      </section>

      <section className="identity-strip" aria-label="Profile facts">
        <div>
          <GraduationCap size={20} />
          <span>Computer Science Grad</span>
        </div>
        <div>
          <MapPin size={20} />
          <span>Toronto area</span>
        </div>
        <div>
          <BriefcaseBusiness size={20} />
          <span>I&apos;m open to junior dev, cloud, and automation roles</span>
        </div>
      </section>

      <section className="experience-section" id="experience">
        <div className="section-heading">
          <p>Experience</p>
          <h2>How I&apos;ve built cloud, automation, and support experience</h2>
        </div>
        <div className="experience-layout">
          <div className="experience-summary">
            <Award size={26} />
            <h3>I bring real cloud exposure, not just coursework</h3>
            <p>
              My resume backs this portfolio with hands-on AWS, Azure, CI/CD,
              Terraform, and CloudFormation experience from an IT/Cloud Support
              internship, plus customer-facing work that sharpened how I
              communicate under pressure. I also deployed this site with AWS
              Amplify and GitHub-based CI/CD to show the cloud workflow behind
              the portfolio itself.
            </p>
            <div className="resume-skill-cloud">
              {['AWS', 'Amplify', 'Azure', 'Terraform', 'CloudFormation', 'CI/CD', 'Python', 'SQL'].map((skill) => (
                <span key={skill}>{skill}</span>
              ))}
            </div>
          </div>

          <div className="timeline">
            {experiences.map((experience) => (
              <article
                className="experience-card"
                key={`${experience.company}-${experience.role}`}
                style={{ '--experience-accent': experience.accent } as React.CSSProperties}
              >
                <div className="experience-meta">
                  <span><Building2 size={16} /> {experience.company}</span>
                  <span><Calendar size={16} /> {experience.date}</span>
                </div>
                <h3>{experience.role}</h3>
                <p className="experience-location">{experience.location}</p>
                <div className="experience-points">
                  {experience.points.map((point) => (
                    <p key={point}>{point}</p>
                  ))}
                </div>
                <div className="chip-row">
                  {experience.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="projects-section" id="projects">
        <div className="section-heading">
          <p>Selected work</p>
          <h2>Click into my projects for the full case study</h2>
        </div>

        <div className="project-showcase">
          <div className="project-tabs" role="tablist" aria-label="Projects">
            {projects.map((project, index) => {
              const Icon = project.icon
              return (
                <button
                  className={activeProject === index ? 'active' : ''}
                  key={project.title}
                  type="button"
                  onClick={() => setActiveProject(index)}
                  role="tab"
                  aria-selected={activeProject === index}
                >
                  <Icon size={18} />
                  <span>{project.title}</span>
                  <ChevronRight className="tab-arrow" size={18} />
                </button>
              )
            })}
          </div>

          <motion.article
            className="project-panel"
            key={selectedProject.title}
            initial={{ opacity: 0, x: 18 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35 }}
            style={{ '--project-accent': selectedProject.accent } as React.CSSProperties}
          >
            <div className="case-study-layout">
              <div className="case-copy">
                <p className="project-eyebrow">{selectedProject.eyebrow}</p>
                <h3>{selectedProject.title}</h3>
                <p>{selectedProject.summary}</p>
                <div className="project-grid">
                  <div>
                    <span>Impact</span>
                    <strong>{selectedProject.metric}</strong>
                  </div>
                  <div>
                    <span>Highlights</span>
                    <strong>{selectedProject.highlights.join(' / ')}</strong>
                  </div>
                </div>
                <div className="chip-row">
                  {selectedProject.stack.map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                </div>
              </div>
              <ProjectMockup project={selectedProject} />
            </div>

            <div className="case-study-detail">
              <section>
                <div className="detail-heading">
                  <Target size={18} />
                  <h4>Project analysis</h4>
                </div>
                <p>{selectedProject.deepDive}</p>
              </section>
              <section>
                <div className="detail-heading">
                  <Zap size={18} />
                  <h4>Why it matters today</h4>
                </div>
                <p>{selectedProject.whyUseful}</p>
              </section>
            </div>

            <div className="case-study-lists">
              <div>
                <h4>How it works</h4>
                {selectedProject.workflow.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
              <div>
                <h4>Modern usefulness</h4>
                {selectedProject.today.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
            </div>
          </motion.article>
        </div>
      </section>

      <section className="stack-section" id="cloud">
        <div className="section-heading">
          <p>Tech stack</p>
          <h2>IT, cloud, and software development toolkit</h2>
        </div>
        <div className="stack-grid">
          {stack.map((item, index) => {
            const Icon = item.icon
            return (
              <motion.div
                className="stack-tile"
                key={item.label}
                whileHover={{ y: -6 }}
                transition={{ type: 'spring', stiffness: 260, damping: 18 }}
              >
                <Icon size={22} />
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
                <small>{String(index + 1).padStart(2, '0')}</small>
              </motion.div>
            )
          })}
        </div>
      </section>

      <section className="notes-section">
        <div className="section-heading">
          <p>Personal signal</p>
          <h2>What makes this portfolio mine</h2>
        </div>
        <div className="notes-list">
          {fieldNotes.map((note) => (
            <div key={note}>
              <Zap size={18} />
              <p>{note}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="contact-section" id="contact">
        <div>
          <p className="status-pill compact">
            <MonitorSmartphone size={16} />
            I&apos;m available for IT, cloud, and software roles
          </p>
          <h2>Let&apos;s connect and build the next thing.</h2>
          <p className="contact-lede">
            I&apos;m looking for junior software development, IT support, cloud
            infrastructure, and automation opportunities where I can keep
            learning while contributing quickly. This portfolio is hosted on
            AWS Amplify with GitHub-based CI/CD.
          </p>
        </div>
        <div className="contact-actions">
          <a href={resumePath} download>
            <Download size={18} />
            Resume
          </a>
          <a href="mailto:Nategomes0@gmail.com">
            <Mail size={18} />
            Email
          </a>
          <a href="tel:+16476277532">
            <Phone size={18} />
            Call
          </a>
          <a href="https://github.com/Nathan-Gomes" target="_blank" rel="noreferrer">
            <ExternalLink size={18} />
            GitHub
          </a>
          <a href="https://www.linkedin.com/in/nathangomes04/" target="_blank" rel="noreferrer">
            <ExternalLink size={18} />
            LinkedIn
          </a>
          <div className="contact-details">
            <p>Nategomes0@gmail.com</p>
            <p>647-627-7532</p>
          </div>
        </div>
      </section>
    </main>
  )
}

export default App
