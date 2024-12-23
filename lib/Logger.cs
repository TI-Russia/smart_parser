﻿using log4net;
using log4net.Appender;
using System;
using System.Collections.Generic;
using System.Reflection;

namespace SmartParser.Lib
{
    public class Logger
    {
        static log4net.Repository.ILoggerRepository repo = LogManager.GetRepository(Assembly.GetEntryAssembly());
        private static void LoadConfig(string resourceName = "Smart.Parser.Lib.Resources.log4net.config") //"SmartParser.Lib.Resources.log4net.config")
        {
            var debug = Assembly.GetExecutingAssembly().GetManifestResourceNames();
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream(resourceName))
            {
                log4net.Config.XmlConfigurator.Configure(repo, stream);
            }
        }

        public static void Setup(string logFileName = "", bool skipLogging = false)
        {
            Errors.Clear();
            if (skipLogging)
            {
                mainLog = null;
                secondLog = null;
            }
            else
            {
                if (String.IsNullOrEmpty(logFileName))
                {
                    logFileName = "smart_parser_" + DateTime.Now.ToString("yyyyMMddHHmmss") + ".log";
                }
                LoadConfig();
                SetLogFileName("Main", logFileName);
                mainLog = LogManager.GetLogger(repo.Name, "Main");
                secondLog = LogManager.GetLogger(repo.Name, "Second");
            } 
            log = mainLog;
        }

        public static void SetupForTests(string mainLogName, string auxLogName)
        {
            mainLog = LogManager.GetLogger(repo.Name, mainLogName);
            secondLog = LogManager.GetLogger(repo.Name, "auxLogName");
            log = mainLog;
        }

        public static void SetSecondLogFileName(string logFileName)
        {
            if (secondLog != null)
            {
                SetLogFileName("Second", logFileName);
            }
        }

        public static void SetLogFileName(string logger, string logFileName)
        {
            bool found = false;
            Errors.Clear();
            var appenders = repo.GetAppenders();
            foreach (log4net.Appender.IAppender a in appenders)
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
            log4net.Repository.Hierarchy.Hierarchy hier = (log4net.Repository.Hierarchy.Hierarchy)LogManager.GetRepository(Assembly.GetExecutingAssembly());
            hier.Root.Level = levels[(int)level];
            hier.RaiseConfigurationChanged(EventArgs.Empty);
            foreach (log4net.Core.ILogger logger in hier.GetCurrentLoggers())
            {
                ((log4net.Repository.Hierarchy.Logger)logger).Level = levels[(int)level];
            }
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
        static public void Debug(string info, params object[] par)
        {
            if (log == null) return;
            log.Debug(String.Format(info.Replace("{", "").Replace("}", ""), par));
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
        }

        static public void Error(string info, params object[] par)
        {
            if (log == null) return;
            string message = String.Format(info, par);
            log.Error(message);
            Errors.Add(message);
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
