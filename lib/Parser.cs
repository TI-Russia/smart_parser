using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Lib
{

    public class Organization
    {

        public Organization(string name, string folder, int person_first, int person_last, bool topLevel)
        {
            this.name = name;
            this.folder = folder;
            this.person_first = person_first;
            this.person_last = person_last;
            this.topLevel = topLevel;
        }

        public string name;
        public string folder;
        public int person_first = -1;
        public int person_last = -1;
        public bool topLevel = false;
    };

    public class Parser
    {
        public int FirstDataRow { set { personsTableStart = value; } get { return personsTableStart; } }
        public int NameOrRelativeTypeColumn { set; get; } = 1;

        public Parser(IAdapter adapter)
        {
            Adapter = adapter;
        }

        public void getPersonsBounds()
        {
            List<int> personStarts = new List<int>();

            int personsTableEnd = Adapter.GetRowsCount();
            //int personsTableEnd = 231;
            for (int i = personsTableStart; i <= personsTableEnd; i++)
            {
                //qDebug() << "person discovery - processing: " << cellAddress;
                Cell currentCell = Adapter.GetCell(i, NameOrRelativeTypeColumn);
                if (!currentCell.IsEmpty && !currentCell.IsHeader)
                {
                    personStarts.Add(i);
                }
                else if (currentCell.IsHeader)
                {
                    headerPositions.Add(i);
                }
            }

            int personStart;
            int personEnd;
            for (int i = 0; i < personStarts.Count() - 1; i++)
            {
                personStart = personStarts[i];
                personEnd = personStarts[i + 1] - 1;
                for (int j = personStarts[i]; j < personStarts[i + 1]; j++)
                {
                    if (headerPositions.IndexOf(j) != -1)
                    {
                        personEnd = j - 1;
                    }
                }
                personBounds.Add(new Tuple<int, int>(personStart, personEnd));
            }
            personStart = personStarts[personStarts.Count() - 1];
            personEnd = personsTableEnd;
            personBounds.Add(new Tuple<int, int>(personStart, personEnd));
            personStarts.Clear();

        }

        void getOrgansBounds()
        {
            int first;
            int second;
            for (int i = 0; i < headerPositions.Count() - 1; i++)
            {
                //qDebug() << i + 1 << " organ start: " << headerPositions.at(i) << "organ end: " << headerPositions.at(i + 1) - 1;
                //qDebug() << "this: " << getExcelCell("A"+QString::number(headerPositions.at(i)))->cellText << "next: " << getExcelCell("A"+QString::number(headerPositions.at(i+1)))->cellText;
                first = headerPositions[i + 1];
                second = headerPositions[i + 1] - 1;
                organsBounds.Add(new Tuple<int, int>(first, second));
            }
            first = headerPositions[headerPositions.Count() - 1] + 1;
            second = Adapter.GetRowsCount();
            organsBounds.Add(new Tuple<int, int>(first, second));
            //qDebug() << headerPositions.length() << " organ start: " << headerPositions.at(headerPositions.length() - 1) << "organ end: " << countUsedRows();
        }

        public void buildOrganList()
        {
            string topOrgName = "";
            foreach (var organPair in organsBounds)
            {
                int personNum = 0;
                int firstPerson = 0;
                int lastPerson = -1;
                bool topLevel = false;
                string orgName = "";

                int organPersonBoundsBegin = 0;
                int organPersonBoundsEnd = 0;

                foreach (var personPair in personBounds)
                {
                    // персона в начале организации
                    if (organPair.Item1 == personPair.Item1)
                    {
                        organPersonBoundsBegin = personNum;
                        firstPerson = personNum;
                        Cell header = Adapter.GetCell("A" + (organPair.Item1 - 1));

                        orgName = header.Text;
                        topLevel = header.ForegroundColor == "ff00b0f0";
                        if (topLevel)
                        {
                            topOrgName = orgName;
                        }
                        //qDebug() << "ORGAN: #" << organPair.first - 1 << " " << header.cellText() << " color bg: " << header.background_color.c_str() << " color fg: " << header.foreground_color.c_str();
                    }
                    // персона в конце организации
                    if (organPair.Item2 == personPair.Item2)
                    {
                        organPersonBoundsEnd = personNum;
                        lastPerson = personNum;
                        organsBoundsList.Add(new Tuple<string, Tuple<int, int>>(orgName, new Tuple<int,int>(organPersonBoundsBegin, organPersonBoundsEnd)));
                        organizations.Add(new Organization(orgName, topOrgName, firstPerson, lastPerson, topLevel));
                        break;
                    }
                    personNum++;
                }
            }
        }

        /*
         
             
             
        */
        Person buildSinglePerson(int boundsBegin, int boundsEnd)
        {
            return null; 
#if false
            //qDebug() << "buildSinglePerson init: bounds " + QString::number(bounds.first) + " - " + QString::number(bounds.second);
            Person person = new Person();
            string  personName = Adapter.GetCell("A" + boundsBegin).Text;
            person.id = (organPersons.Count() + 1);
            if (relationTypes.IndexOf(personName) == -1)
            {
                person.name = personName;
            }
            else
            {
                person.setRelationType(relationTypes.IndexOf(personName));
                for (int i = organPersons.Count() - 1; i >= 0; i--)
                {
                    Person currentPerson = organPersons[i];
                    if (!string.IsNullOrEmpty(currentPerson.name))
                    {
                        person.id = currentPerson.id;
                        break;
                    }
                }
            }
            string positionText = Adapter.GetCell("B" + boundsBegin.ToString()).Text;

            person.role = positionText; // + currentOrg.name
            //person.po.setPosition(positionText + " " + currentOrg.name);
            //ExcelCell cell;
            for (int i = boundsBegin; i <= boundsEnd; i++)
            {
                Cell cell = Adapter.GetCell("C" + i);
                //ExcelCell cell = Adapter.Cell("C" + QString::number(i));
                if (!cell.IsEmpty)
                {
                    //Realty* realty = new Realty();
                    Real_Estates realty = new Real_Estates();
                    realty.name = cell.Text;
                    //realty.setRealtyType(1);
                    int objectType = 0;
                    if (objectTypes.ContainsKey(cell.Text))
                    {
                        objectTypes.TryGetValue(cell.Text, out objectType);
                    }
                    realty.type = cell.Text;
                    //realty.setObjectType(objectType);
                    cell = Adapter.GetCell("D" + i);
                    int ownershipType = 0;
                    double ownershipPart = 0;
                    string text = cell.Text.Trim();
                    if (!ownershipTypes.ContainsKey(text))
                    {
                        if (text.IndexOf("-") != -1) // pre 2015 version
                        {
                            string option = text.Split('-')[0].Trim();
                            if (option == "общая долевая")
                            {
                                ownershipType = 3;
                                string ownershipPartText = text.Split('-')[1].Trim();
                                if (ownershipPartText.IndexOf("/") != -1)
                                {
                                    ownershipPart = Convert.ToDouble(ownershipPartText.Split('/')[0]) / Convert.ToDouble(ownershipPartText.Split('/')[1]);
                                }
                            }
                        }
                        else
                        {
                            //    ownershipType = 0;
                            //}
                            String[] parts = text.Split(' ');
                            if (parts.Length == 2 && parts[0] == "долевая")
                            {
                                ownershipType = 3;
                                String[] fraction = parts[1].Split('/');
                                if (fraction.Length == 2)
                                {
                                    ownershipPart = Convert.ToDouble(fraction[0]) / Convert.ToDouble(fraction[1]);
                                }
                                else
                                {
                                    //qDebug() << "error: cannot parse ownership text " << text;
                                    errorCount++;
                                }
                            }
                            else
                            {
                                //qDebug() << "error: cannot parse ownership text " << text;
                                errorCount++;
                            }
                        }
                    }
                    else
                    {
                         ownershipTypes.TryGetValue(text, out ownershipType);
                    }
                    realty.share_amount = (float)ownershipPart;
                    //realty.setOwnershipType(o`wnershipType);
                    //realty..setOwnershipText(text);

                    cell = Adapter.GetCell("E" + i);
                    string number = cell.Text.Replace(" ", "");
                    number = number.Replace(",", ".");
                    double square = Convert.ToDouble(number);
                    realty.square = (float)square;
                    cell = Adapter.GetCell("F" + i);
                    string countryStr = cell.Text;
                    int country;
                    //if (!cell.IsEmpty)
                    //{
                    //    if ( && countries.indexOf(cell.cellText()) != -1)
                    //    country = countries.indexOf(cell.cellText());
                    //}
                    //else
                    //{
                    //    country = 0;
                    //}
                    realty.country = countryStr;
                    //person..addRealty(realty);
                }
                else
                {
                    break;
                }
            }
            for (int i = boundsBegin; i <= boundsEnd; i++)
            {
                Cell cell = Adapter.GetCell("G" + i);
                if (!cell.IsEmpty)
                {
                    Real_Estates realty = new Real_Estates();
                    realty.name = cell.Text;
                    //realty.setRealtyType(2);
                    int objectType = 0;
                    if (objectTypes.indexOf(cell.cellText()) != -1)
                    {
                        objectType = objectTypes.indexOf(cell.cellText());
                    }
                    realty.setObjectType(objectType);
                    cell = Adapter.Cell("H" + QString::number(i));
                    string number = cell.cellText().split(" ").join("");
                    number = number.Replace(",", ".");
                    double square = Convert.ToDouble(cell.Text);
                    realty.setSquare(square);
                    cell = Adapter.Cell("I" + QString::number(i));
                    int country;
                    if (!cell.isEmpty && countries.indexOf(cell.cellText()) != -1)
                    {
                        country = countries.indexOf(cell.cellText());
                    }
                    else
                    {
                        country = 0;
                    }
                    realty.setCountry(country);
                    person.addRealty(realty);
                }
                else
                {
                    break;
                }
            }
            for (int i = boundsBegin; i <= boundsEnd; i++)
            {
                ExcelCell cell = Adapter.Cell("J" + QString::number(i));
                if (!cell.isEmpty)
                {
                    Transport transport;
                    transport.setName(cell.cellText());
                    person.addTransport(transport);
                }
                else
                {
                    break;
                }
            }
            ExcelCell cell = Adapter.Cell("K" + QString::number(bounds.first));
            QString incomeText = cell.cellText();
            if (incomeText.indexOf("(") != -1)
            {
                int leftBrace = incomeText.indexOf("(");
                int rightBrace = incomeText.indexOf(")");
                int length = rightBrace - leftBrace - 1;
                QString incomeComment = incomeText.mid(leftBrace + 1, length);
                person.setIncomeComment(incomeComment);
                QString income = incomeText.left(leftBrace).trimmed();
                income = income.replace(QString(","), QString("."));
                person.setIncome(income.toDouble());
            }
            else
            {
                incomeText = incomeText.trimmed();
                incomeText = incomeText.split(" ").join("");
                incomeText = incomeText.replace(QString(","), QString("."));
                person.setIncome(incomeText.toDouble());
            }
            cell = Adapter.Cell("L" + QString::number(bounds.first));
            person.setIncomeSource(cell.cellText());
            organPersons.append(person);
            return person;
#endif
        }

        void singlePersonToJSON(Person person)
        {
        }

        void personListToJSON(List<Person> personList)
        {
            //QListIterator<Person> iter(personList);
            int current = 1;
            int all = personList.Count();
            //while (iter.hasNext())
            foreach(Person person in personList)
            {
                //qDebug() << "converting to XML: " + QString::number(current) + " of " + QString::number(all);
                singlePersonToJSON(person);
                current++;
            }
        }

        List<Person> buildPersonObjects(List<Tuple<int, int>> bounds)
        {
            List<Person> persons = new List<Person>();
            int current = 1;
            int all = personBounds.Count();
            //QListIterator<QPair<int, int>> iter(bounds);
            //while (iter.hasNext())
            foreach(var currentPair in bounds)
            {
                //QPair<int, int> currentPair = iter.next();
                //qDebug() << "building person objects: " + QString::number(current) + " of " + QString::number(all);
                persons.Add(buildSinglePerson(currentPair.Item1, currentPair.Item2));
                current++;
            }
            return persons;
        }

        void buildOrgansJSON()
        {
            foreach (Organization currentOrg in organizations)
            {
                if (currentOrg.name == "")
                {
                    //qDebug() << "Error: empty org";
                    continue;
                }
                List<Tuple<int, int>> personsBounds = new List<Tuple<int, int>>();
                //for (int i = pair.second.first; i <= pair.second.second; i++) {
                for (int i = currentOrg.person_first; i <= currentOrg.person_last; i++)
                {
                    personsBounds.Add(personBounds[i]);
                }
                List<Person> personsList = buildPersonObjects(personsBounds);
            }

            //qDebug() << "building organs XMLs with organsBoundsList length: " << organsBoundsList.length();
            //QListIterator<QPair<QString, QPair<int, int>>> iter(organsBoundsList);

            //QListIterator<Organization> iter(organizations);
            //while (iter.hasNext())
            foreach(Organization currentOrg in organizations)
            {
                organPersons.Clear();
                //QPair<QString, QPair<int, int>> pair = iter.next();
                //currentOrgan = pair.first;
                //currentOrg = iter.next();
                if (currentOrg.name == "")
                {
                    //qDebug() << "Error: empty org";
                    continue;
                }
                //QList<QPair<int, int>> personsBounds;
                List<Tuple<int, int>> personsBounds = new List<Tuple<int, int>>();
                //for (int i = pair.second.first; i <= pair.second.second; i++) {
                for (int i = currentOrg.person_first; i <= currentOrg.person_last; i++)
                {
                    personsBounds.Add(personBounds[i]);
                }
                List<Person> personsList = buildPersonObjects(personsBounds);

                //startXMLDocument();
                personListToJSON(personsList);
                //finalizeXMLDocument();


                //qDebug() << "the organ is: " << pair.first;
                //qDebug() << "starts with person: " << pair.second.first;
                //qDebug() << "ends with person: " << pair.second.second;
                //qDebug() << "the organ is: " << currentOrg.name;
                //qDebug() << "starts with person: " << currentOrg.person_first;
                //qDebug() << "ends with person: " << currentOrg.person_last;
            }
            //qDebug() << u8"Процесс конвертации завершён";
            //qDebug() << "total persons: " << personBounds.length();
            //qDebug() << "total errors: " << errorCount;
        }

        public void DumpColumn(int column)
        {
            int personsTableEnd = Adapter.GetRowsCount() - 1;
            //StreamWriter standardOutput = new StreamWriter(Console.OpenStandardOutput());
            for (int i = personsTableStart; i <= personsTableEnd; i++)
            {
                //qDebug() << "person discovery - processing: " << cellAddress;
                Cell currentCell = Adapter.GetCell(i, NameOrRelativeTypeColumn);

                Console.WriteLine(JsonWriter.SerializeCell(currentCell));
            }
        }
        public void Process()
        {
            getPersonsBounds();
            getOrgansBounds();
            buildOrganList();
            buildOrgansJSON();
        }

        IAdapter Adapter { get; set; }



        int personsTableStart = 4;

        List<Tuple<int, int>> personBounds = new List<Tuple<int, int>>();
        List<Tuple<int, int>> organsBounds = new List<Tuple<int, int>>();
        List<int> headerPositions = new List<int>();
        List<Organization> organizations = new List<Organization>();
        List<Tuple<string, Tuple<int, int>>> organsBoundsList = new List<Tuple<string, Tuple<int, int>>>();
        List<Person> organPersons = new List<Person>();

        List<string> relationTypes = new List<string>();

        Dictionary<string, int> ownershipTypes = new Dictionary<string, int>();
        Dictionary<string, int> objectTypes = new Dictionary<string, int>();

        int errorCount = 0;

    }
}
