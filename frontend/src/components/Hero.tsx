const Hero = () => {
  return (
    <section className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-950 via-slate-900 to-violet-950 text-white px-6">
      <div className="max-w-5xl text-center">

        {/* TITLE */}
        <h1 className="text-4xl md:text-6xl font-extrabold leading-tight">
          AI-Based Intelligent Notes Summarizer
          <br />
          <span className="text-indigo-400">
            and Recommendation System
          </span>
        </h1>

        {/* SUBTITLE */}
        <p className="mt-6 text-lg text-slate-300">
          Convert lengthy academic materials into concise, meaningful,
          and intelligent summaries using AI-powered techniques.
        </p>

        {/* BUTTONS */}
        <div className="mt-10 flex flex-wrap justify-center gap-6">
          <button className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition font-semibold shadow-lg shadow-indigo-500/20">
            Save Time
          </button>

          <button className="px-6 py-3 rounded-xl bg-violet-600 hover:bg-violet-500 transition font-semibold shadow-lg shadow-violet-500/20">
            Learn Faster
          </button>

          <button className="px-6 py-3 rounded-xl bg-fuchsia-600 hover:bg-fuchsia-500 transition font-semibold shadow-lg shadow-fuchsia-500/20">
            Study Smarter
          </button>
        </div>
      </div>
    </section>
  );
};

export default Hero;
