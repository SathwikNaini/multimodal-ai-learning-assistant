import { Brain, GraduationCap, Mail, Github, Linkedin } from 'lucide-react';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-slate-950 text-white py-12 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-indigo-600 p-2 rounded-lg">
                <Brain className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold">AI Notes Summarizer</h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">
              Transforming academic learning through intelligent AI-powered summarization and
              personalized recommendations.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4 flex items-center gap-2">
              <GraduationCap className="w-5 h-5 text-indigo-400" />
              Academic Project
            </h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li>Final Year Engineering Project</li>
              <li>Computer Science & Engineering</li>
              <li>Artificial Intelligence & NLP</li>
              <li>Educational Technology</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Connect</h4>
            <div className="flex gap-4">
              <a
                href="#"
                className="bg-gray-800 hover:bg-indigo-600 p-3 rounded-lg transition-colors duration-200"
                aria-label="Email"
              >
                <Mail className="w-5 h-5" />
              </a>
              <a
                href="#"
                className="bg-gray-800 hover:bg-indigo-600 p-3 rounded-lg transition-colors duration-200"
                aria-label="GitHub"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="#"
                className="bg-gray-800 hover:bg-indigo-600 p-3 rounded-lg transition-colors duration-200"
                aria-label="LinkedIn"
              >
                <Linkedin className="w-5 h-5" />
              </a>
            </div>
            <p className="text-sm text-gray-400 mt-4">
              Built with React, TypeScript, and Tailwind CSS
            </p>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-gray-400">
              {currentYear} AI-Based Intelligent Notes Summarizer. Academic Research Project.
            </p>
            <div className="flex gap-6 text-sm text-gray-400">
              <a href="#" className="hover:text-blue-400 transition-colors">
                Privacy Policy
              </a>
              <a href="#" className="hover:text-blue-400 transition-colors">
                Terms of Use
              </a>
              <a href="#" className="hover:text-blue-400 transition-colors">
                Documentation
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
