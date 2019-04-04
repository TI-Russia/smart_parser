using log4net;
using log4net.Appender;
using log4net.Config;
using log4net.Layout;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

namespace Parser.Lib
{


    public class Logger
    {
        private const int MaxErrorCount = 150;

        private static void LoadConfig()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Parser.Lib.Resources.log4net.config"))
            {
                log4net.Config.XmlConfigurator.Configure(stream);
            }
        }

        public static void Setup(string logFileName = "")
        {
            Errors.Clear();
            if (String.IsNullOrEmpty(logFileName))
            {
                logFileName = "smart_parser_" + DateTime.Now.ToString("yyyyMMddHHmmss") + ".log";
            }
            LoadConfig();
            SetLogFileName("Main", logFileName);
            mainLog = LogManager.GetLogger("Main");
            secondLog = LogManager.GetLogger("Second");
            log = mainLog;
        }

        public static void SetupForTests(string mainLogName, string auxLogName)
        {
            mainLog = LogManager.GetLogger(mainLogName);
            secondLog = LogManager.GetLogger("auxLogName");
            log = mainLog;
        }

        public static void SetSecondLogFileName(string logFileName)
        {
            SetLogFileName("Second", logFileName);
        }

        public static void SetLogFileName(string logger, string logFileName)
        {
            bool found = false;
            Errors.Clear();
            //XmlConfigurator.Configure();
            log4net.Repository.Hierarchy.Hierarchy h =
            (log4net.Repository.Hierarchy.Hierarchy)LogManager.GetRepository();

            foreach (log4net.Appender.IAppender a in
           log4net.LogManager.GetRepository().GetAppenders())
            {
                if (a is FileAppender && a.Name == logger)
                {
                    FileAppender fa = (FileAppender)a;

                    fa.AppendToFile = false;
                    fa.File = logFileName;
                    fa.ActivateOptions();
                    found = true;
                    break;
                }
            }
            if (!found)
            {
                throw new Exception("Cannot find Appender " + logger);
            }
        }

        public enum LogLevel
        {
            Debug = 0,
            Info,
            Error
        };
        static public void SetLoggingLevel(LogLevel level)
        {
            log4net.Core.Level[] levels = { log4net.Core.Level.Debug, log4net.Core.Level.Info, log4net.Core.Level.Error };
            ((log4net.Repository.Hierarchy.Hierarchy) LogManager.GetRepository()).Root.Level = levels[(int)level];
            ((log4net.Repository.Hierarchy.Hierarchy) LogManager.GetRepository()).RaiseConfigurationChanged(EventArgs.Empty);
        }
        public static ILog Log { get { return log; } }
        public static ILog SecondLog { get { return secondLog; } }

        private static ILog log;
        private static ILog mainLog;
        private static ILog secondLog;

        static public void SetOutMain()
        {
            log = mainLog;
        }
        static public void SetOutSecond()
        {
            log = secondLog;
        }

        static public void Info(string info, params object[] par)
        {
            if (log == null) return;
            log.Info(String.Format(info, par));
        }
        static public void Info(string info)
        {
            if (log == null) return;
            log.Info(String.Format(info));
        }
        static public void UnknownRealEstateType(string info)
        {
            UnknownRealEstate.Add(info);
        }
        static public void Error(int row, string info, params object[] par)
        {
            if (log == null) return;
            string message = String.Format(info, par);
            log.Error(string.Format("row {0}: {1}", row,  message));
            Errors.Add(message);
            if (Errors.Count() > MaxErrorCount)
            {
                throw new SmartParserException("Error count exceed " + MaxErrorCount.ToString());
            }
        }

        static public void Error(string info, params object[] par)
        {
            if (log == null) return;
            string message = String.Format(info, par);
            log.Error(message);
            Errors.Add(message);
            if (Errors.Count() > MaxErrorCount)
            {
                throw new SmartParserException("Error count exceed " + MaxErrorCount.ToString());
            }
        }

        static public void Info2(string info, params object[] par)
        {
            secondLog.Info(String.Format(info, par));
        }
        static public void Info2(string info)
        {
            secondLog.Info(String.Format(info));
        }
        static public void Error2(string info, params object[] par)
        {
            string message = String.Format(info, par);
            secondLog.Error(message);
            Errors.Add(message);
        }

        public static HashSet<string> Errors { get; } = new HashSet<string>();
        public static HashSet<string> UnknownRealEstate { get; } = new HashSet<string>();
    }
}
