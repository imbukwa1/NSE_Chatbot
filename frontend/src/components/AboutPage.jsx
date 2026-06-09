import audryProfile from '../assets/images/audry-profile.jpg'
import aiAssistanceImage from '../assets/images/ai-assistance.jpg'
import capabilityImage1 from '../assets/images/capability-1.png'
import capabilityImage2 from '../assets/images/capability-2.png'
import capabilityImage3 from '../assets/images/capability-3.png'
import capabilityImage4 from '../assets/images/capability-4.png'
import capabilityImage5 from '../assets/images/capability-5.png'
import capabilityImage6 from '../assets/images/capability-6.png'
import learningImage from '../assets/images/learning.jpg'
import nseIpoImage from '../assets/images/nse-ipo.jpg'
import tradePicture from '../assets/images/trade-pictures.jpg'

function SectionHeading({ eyebrow, title, children }) {
  return (
    <div className="mx-auto max-w-3xl text-center">
      {eyebrow && (
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600">
          {eyebrow}
        </p>
      )}
      <h2 className="mt-2 text-3xl font-semibold text-slate-950 sm:text-4xl">
        {title}
      </h2>
      {children && (
        <p className="mt-4 text-base leading-8 text-slate-600">{children}</p>
      )}
    </div>
  )
}

function FeatureCard({ title, description, icon, image, imageAlt }) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-blue-100 hover:shadow-[0_18px_45px_rgba(96,126,203,0.12)]">
      {image && (
        <div className="aspect-[16/9] w-full overflow-hidden bg-slate-100">
          <img
            src={image}
            alt={imageAlt || ''}
            className="h-full w-full object-cover object-center"
          />
        </div>
      )}
      <div className="flex flex-1 flex-col p-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-sm font-semibold text-blue-700">
          {icon}
        </div>
        <h3 className="mt-4 text-base font-semibold text-slate-950">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
      </div>
    </div>
  )
}

function FlowStep({ index, title, description }) {
  return (
    <div className="relative rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
        {index}
      </span>
      <h3 className="mt-4 text-base font-semibold text-slate-950">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
    </div>
  )
}

function InsightMockup() {
  // Static mockup explains the product without depending on live backend data.
  return (
    <div className="relative mx-auto w-full max-w-lg">
      <div className="absolute -left-3 top-8 hidden rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-[0_18px_45px_rgba(96,126,203,0.13)] sm:block">
        <p className="text-xs text-slate-400">AI signal</p>
        <p className="mt-1 text-sm font-semibold text-emerald-600">Beginner-ready</p>
      </div>
      <div className="rounded-[2rem] border border-white bg-white/90 p-5 shadow-[0_28px_80px_rgba(96,126,203,0.18)]">
        <div className="rounded-[1.5rem] border border-slate-100 bg-slate-50 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-950">NSE AI Advisor</p>
              <p className="mt-1 text-xs text-slate-500">Simple market research</p>
            </div>
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              AI
            </span>
          </div>
          <div className="mt-5 space-y-3">
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-400">User question</p>
              <p className="mt-2 text-sm font-medium text-slate-800">
                What does Safaricom dividend yield mean?
              </p>
            </div>
            <div className="rounded-2xl bg-blue-600 p-4 text-white shadow-[0_16px_32px_rgba(37,99,235,0.2)]">
              <p className="text-xs text-blue-100">AI explanation</p>
              <p className="mt-2 text-sm leading-6">
                Dividend yield shows the annual dividend compared with the share price,
                helping beginners understand income potential.
              </p>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-400">Source</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">NSE data</p>
            </div>
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <p className="text-xs text-slate-400">Purpose</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">Education</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AboutPage({ onStartChatting, onBackHome }) {
  // Keep this content educational and stable; app data belongs in the chat/profile screens.
  const platformFeatures = [
    ['AI Stock Questions', 'Ask natural-language questions about NSE-listed companies.', 'Q', capabilityImage1],
    ['Market Overview', 'Review simple market movers and market snapshot summaries.', 'M', capabilityImage2],
    ['Simplified Analysis', 'Turn technical market information into readable explanations.', 'A', capabilityImage3],
    ['NSE Learning Support', 'Learn investing terms, dividends, valuation, and risk basics.', 'L', capabilityImage4],
    ['Company Comparisons', 'Compare selected companies in a beginner-friendly format.', 'C', capabilityImage5],
    ['AI Investment Insights', 'Receive educational insight summaries with clear disclaimers.', 'I', capabilityImage6],
  ]

  const tags = ['NSE Market Data', 'AI Analysis', 'Market Snapshots', 'Educational Insights']

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,_#f8fafc_0%,_#f3f6fb_56%,_#eef2f8_100%)] text-slate-900">
      <nav className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
        <button
          type="button"
          onClick={onBackHome}
          className="flex items-center gap-3 text-left"
          aria-label="NSE AI Advisor home"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-sm font-bold text-white shadow-[0_12px_28px_rgba(37,99,235,0.28)]">
            NSE
          </span>
          <span>
            <span className="block text-base font-semibold text-slate-900">
              NSE AI Advisor
            </span>
            <span className="block text-xs text-slate-500">
              Nairobi Securities Exchange
            </span>
          </span>
        </button>
        <div className="hidden items-center gap-8 text-sm font-medium text-slate-500 md:flex">
          <button type="button" onClick={onBackHome} className="hover:text-blue-600">
            Home
          </button>
          <button type="button" onClick={onStartChatting} className="hover:text-blue-600">
            AI Chatbot
          </button>
          <button type="button" className="text-blue-600">
            About
          </button>
        </div>
        <button
          type="button"
          onClick={onStartChatting}
          className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_26px_rgba(37,99,235,0.22)] transition hover:bg-blue-700"
        >
          Start Chatting
        </button>
      </nav>

      <main>
        <section className="mx-auto grid w-full max-w-7xl items-center gap-12 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_0.9fr] lg:px-10 lg:py-16">
          <div>
            <div className="inline-flex rounded-full border border-blue-100 bg-white px-4 py-2 text-sm font-medium text-blue-700 shadow-sm">
              AI-Powered NSE Research
            </div>
            <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-tight text-slate-950 sm:text-5xl lg:text-6xl">
              About NSE AI Advisor
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
              An AI-powered assistant helping users explore the Nairobi Securities Exchange
              through simple conversations, market insights, and beginner-friendly stock research.
            </p>
            <button
              type="button"
              onClick={onStartChatting}
              className="mt-8 rounded-full bg-blue-600 px-7 py-4 text-sm font-semibold text-white shadow-[0_18px_32px_rgba(37,99,235,0.24)] transition hover:bg-blue-700"
            >
              Start Chatting
            </button>
          </div>
          <InsightMockup />
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
          <SectionHeading title="Our Mission">
            Our mission is to simplify access to Nairobi Securities Exchange information using
            conversational AI, making stock research easier for students, beginners, and everyday investors.
          </SectionHeading>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            <FeatureCard
              title="Simple Insights"
              description="Easy-to-understand market explanations."
              icon="01"
              image={nseIpoImage}
              imageAlt="IPO market chart illustrating NSE investment insights"
            />
            <FeatureCard
              title="Accessible Learning"
              description="Designed for beginner-friendly NSE exploration."
              icon="02"
              image={learningImage}
              imageAlt="People learning to understand financial market charts"
            />
            <FeatureCard
              title="AI Assistance"
              description="Conversational stock research powered by AI."
              icon="03"
              image={aiAssistanceImage}
              imageAlt="People working together with artificial intelligence"
            />
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
          <div className="mb-12 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_18px_50px_rgba(96,126,203,0.1)]">
            <img
              src={tradePicture}
              alt="Financial assets available for trading"
              className="h-64 w-full object-contain object-center p-4 sm:h-80 sm:p-6"
            />
          </div>
          <SectionHeading title="What The Platform Does" eyebrow="Capabilities">
            A focused set of tools for learning, exploring, and asking better questions about the NSE.
          </SectionHeading>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {platformFeatures.map(([title, description, icon, image]) => (
              <FeatureCard
                key={title}
                title={title}
                description={description}
                icon={icon}
                image={image}
                imageAlt={`${title} illustration`}
              />
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
          <div className="rounded-[2rem] border border-slate-200 bg-white/90 p-6 shadow-[0_18px_50px_rgba(96,126,203,0.1)] sm:p-8">
            <SectionHeading title="How It Works" eyebrow="AI workflow">
              The system turns a simple question into a clear, educational market response.
            </SectionHeading>
            <div className="mt-10 grid gap-4 lg:grid-cols-4">
              <FlowStep index="1" title="Ask a Question" description="Type a stock, market, dividend, valuation, or comparison question." />
              <FlowStep index="2" title="AI Processes NSE Market Data" description="The assistant checks available market snapshots and cached company context." />
              <FlowStep index="3" title="System Analyzes Company Information" description="Relevant stock signals are organized into a simpler explanation." />
              <FlowStep index="4" title="User Receives Simplified Insights" description="The final response is concise, conversational, and beginner-friendly." />
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
          <div className="grid gap-8 rounded-[2rem] border border-blue-100 bg-blue-50/70 p-6 sm:p-8 lg:grid-cols-[1fr_0.9fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
                Data and intelligence
              </p>
              <h2 className="mt-2 text-3xl font-semibold text-slate-950">
                Powered by Market Data & AI
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-700">
                NSE AI Advisor combines NSE market information, AI-powered analysis, and
                simplified investment explanations to help users explore the market more confidently.
              </p>
            </div>
            <div className="flex flex-wrap content-center gap-3">
              {tags.map((tag, index) => (
                <span
                  key={tag}
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    index % 2 === 0
                      ? 'bg-white text-blue-700 shadow-sm'
                      : 'bg-emerald-50 text-emerald-700'
                  }`}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-5 py-12 sm:px-8 lg:px-10">
          <h2 className="text-center text-3xl font-semibold text-slate-950 sm:text-4xl">
            Meet the Team
          </h2>
          <div className="mx-auto mt-8 max-w-[52rem] rounded-[2.2rem] border border-slate-200 bg-white p-7 shadow-[0_20px_56px_rgba(96,126,203,0.11)] sm:p-9">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
              <img
                src={audryProfile}
                alt="Audry Imbukwa Bakhoya"
                className="h-28 w-28 shrink-0 rounded-3xl object-cover object-center shadow-[0_16px_32px_rgba(37,99,235,0.18)] ring-4 ring-blue-50 sm:h-32 sm:w-32"
              />
              <div>
                <h3 className="text-2xl font-semibold text-slate-950">
                  Audry Imbukwa Bakhoya
                </h3>
                <p className="mt-1 text-base font-medium text-blue-700">
                  Software Engineer & Project Lead
                </p>
                <p className="mt-4 text-[15px] leading-8 text-slate-600">
                  Passionate about building AI-powered systems that simplify access to financial
                  and educational information through modern software engineering.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200/80 bg-white/70 px-5 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 text-sm text-slate-500 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-semibold text-slate-900">NSE AI Advisor</p>
            <p className="mt-1 text-xs text-slate-400">This is not financial advice.</p>
          </div>
          <div className="flex flex-wrap gap-4">
            {['About', 'AI Chatbot', 'Market Overview'].map((item) => (
              <button
                key={item}
                type="button"
                onClick={item === 'AI Chatbot' ? onStartChatting : undefined}
                className="transition hover:text-blue-600"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}

export default AboutPage
