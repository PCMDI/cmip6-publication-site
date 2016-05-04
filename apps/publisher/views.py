from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.forms import forms, formset_factory, modelformset_factory
from forms import PublicationForm, AuthorForm, BookForm, ConferenceForm, JournalForm, MagazineForm, PosterForm
from forms import PresentationForm, TechnicalReportForm, OtherForm
from forms import ExperimentForm, FrequencyForm, KeywordForm, ModelForm, VariableForm
from datetime import date
from django.http import JsonResponse, HttpResponseRedirect
from models import *
import requests


# Helper functions
def save_publication(pub_form, request, author_form_set, pub_type):
    publication = pub_form.save(commit=False)
    publication.submitter = request.user
    publication.publication_type = pub_type
    publication.save()
    publication.frequency.add(*[Frequency.objects.get(id=frequency_id) for frequency_id in request.POST.getlist("frequency")])
    publication.keywords.add(*[Keyword.objects.get(id=keywords_id) for keywords_id in request.POST.getlist("keyword")])
    publication.model.add(*[Model.objects.get(id=model_id) for model_id in request.POST.getlist("model")])
    publication.variables.add(*[Variable.objects.get(id=variable_id) for variable_id in request.POST.getlist("variable")])
    publication.save()  # might not be needed
    ensemble = request.POST.getlist('ensemble')
    experiments = request.POST.getlist('experiment')
    PubModels.objects.filter(publication=publication.id).exclude(experiment__in=experiments).delete()
    # Delete any experiments that were unchecked
    for exp_id in experiments:
        exp = Experiment.objects.get(id=exp_id)
        ens = ensemble[exp.id - 1]  # database index vs lists, so off by one
        pubmodel = PubModels.objects.filter(publication=publication.id, experiment=exp_id)
        if ens: # Enforce that experiments must have an ensemble
            if pubmodel:
                pubmodel[0].ensemble = int(ens)
                pubmodel[0].save()
            else:
                PubModels.objects.create(publication=publication, experiment=exp, ensemble=ens)
    for authorform in author_form_set:
        author = authorform.save()
        publication.authors.add(author.id)
    return publication


def get_all_options():
    all_options = {}
    all_options['experiment'] = "Experiment"
    all_options['frequency'] = "Frequency"
    all_options['keyword'] = "Keyword"
    all_options['model'] = "Model"
    all_options['status'] = "Status"
    all_options['type'] = "Type"
    all_options['variable'] = "Variable"
    all_options['year'] = "Year"
    return all_options


@login_required()
def search(request):
    pubs = {}
    data = {}
    pubs["type"] = request.GET.get("type", "all")
    pubs["option"] = request.GET.get("option", "")
    pubs["total"] = Publication.objects.all().count()

    if request.method == 'GET':
        pubs["search"] = True
        page_filter = request.GET.get("type", "all")

        if page_filter == 'all':
            publications = Publication.objects.all()
            pubs["pages"] = get_all_options()

        elif page_filter == 'experiment':
            option = request.GET.get("option", "1pctCO2")
            pubs["option"] = request.GET.get("option", "1pctCO2")
            publications = Publication.objects.filter(experiments=Experiment.objects.filter(experiment=option))
            for exp in Experiment.objects.all():
                if Publication.objects.filter(experiments=Experiment.objects.filter(experiment=exp)).count() == 0:
                    continue
                exps = {}
                exps['type'] = 'experiment'
                exps['options'] = str(exp.experiment)
                exps['count'] = Publication.objects.filter(experiments=Experiment.objects.filter(experiment=exp)).count()
                data[str(exp.experiment)] = exps
            pubs["pages"] = data

        elif page_filter == 'frequency':
            option = request.GET.get("option", "3-hourly")
            pubs["option"] = request.GET.get("option", "3-hourly")
            publications = Publication.objects.filter(frequency=Frequency.objects.filter(frequency=option))
            for frq in Frequency.objects.all():
                if Publication.objects.filter(frequency=Frequency.objects.filter(frequency=frq)).count() == 0:
                    continue
                frqs = {}
                frqs['type'] = 'frequency'
                frqs['options'] = str(frq.frequency)
                frqs['count'] = Publication.objects.filter(frequency=Frequency.objects.filter(frequency=frq)).count()
                data[str(frq.frequency)] = frqs
            pubs["pages"] = data

        elif page_filter == 'keyword':
            option = request.GET.get("option", "Abrupt change")
            pubs["option"] = request.GET.get("option", "Abrupt change")
            publications = Publication.objects.filter(keywords=Keyword.objects.filter(keyword=option))
            for kyw in Keyword.objects.all():
                if Publication.objects.filter(keywords=Keyword.objects.filter(keyword=kyw)).count() == 0:
                    continue
                kyws = {}
                kyws['type'] = 'keyword'
                kyws['options'] = str(kyw.keyword)
                kyws['count'] = Publication.objects.filter(keywords=Keyword.objects.filter(keyword=kyw)).count()
                data[str(kyw.keyword)] = kyws
            pubs["pages"] = data

        elif page_filter == 'model':
            option = request.GET.get("option", "ACCESS1.0")
            pubs["option"] = request.GET.get("option", "ACCESS1.0")
            publications = Publication.objects.filter(model=Model.objects.filter(model=option))
            for mod in Model.objects.all():
                if Publication.objects.filter(model=Model.objects.filter(model=mod)).count() == 0:
                    continue
                mods = {}
                mods['type'] = 'model'
                mods['options'] = str(mod.model)
                mods['count'] = Publication.objects.filter(model=Model.objects.filter(model=mod)).count()
                data[str(mod.model)] = mods
            pubs["pages"] = data


        elif page_filter == 'status':
            option = request.GET.get("option", "0")
            if option != "0":
                if option == 'Published':
                    option = 0
                elif option == 'Submitted':
                    option = 1
                elif option == 'Accepted':
                    option = 2
                else:
                    option = 3
            publications = Publication.objects.filter(status=option)
            for stat in [0, 1, 2, 3]:
                if Publication.objects.filter(status=stat).count() == 0:
                    continue
                stats = {}
                stats['type'] = 'status'
                if stat == 0:
                    option = 'Published'
                elif stat == 1:
                    option = 'Submitted'
                elif stat == 2:
                    option = 'Accepted'
                else:
                    option = 'Not Applicable'
                stats['options'] = option
                stats['count'] = Publication.objects.filter(status=stat).count()
                data[str(stat)] = stats
            pubs["pages"] = data

        elif page_filter == 'type':
            option = request.GET.get("option", "2")
            publications = Publication.objects.filter(publication_type=option)

        elif page_filter == 'variable':
            option = request.GET.get("option", "air pressure")
            pubs["option"] = request.GET.get("option", "air pressure")
            publications = Publication.objects.filter(variables=Variable.objects.filter(variable=option))
            for var in Variable.objects.all():
                if Publication.objects.filter(variables=Variable.objects.filter(variable=var)).count() == 0:
                    continue
                vars = {}
                vars['type'] = 'variable'
                vars['options'] = str(var.variable)
                vars['count'] = Publication.objects.filter(variables=Variable.objects.filter(variable=var)).count()
                data[str(var.variable)] = vars
            pubs["pages"] = data

        elif page_filter == 'year':
            # TODO - filter by year not date
            option = request.GET.get("option", str(date.today()))
            pubs["option"] = request.GET.get("option", str(date.today()))
            publications = Publication.objects.filter(publication_date=option)

        pubs["publications"] = publications
    return render(request, 'site/search.html', pubs)


@login_required()
def review(request):
    message = None
    entries = Publication.objects.filter(submitter=request.user.id)
    if not entries:
        message = 'You do not have any publications to display. <a href="/new">Submit one.</a>'
    return render(request, 'site/review.html', {'message': message, 'entries': entries, 'error': None})


@login_required()
def delete(request, pub_id):
    publication = Publication.objects.get(id=pub_id)
    userid = request.user.id
    if userid == publication.submitter.id:
        publication.delete()
        return redirect('review')
    else:
        entries = Publication.objects.filter(submitter=userid)
        error = 'Error: You must be the owner of a submission to edit it.'
        return render(request, 'site/review.html', {'message': None, 'entries': entries, 'error': error})


@login_required()
def edit(request, pubid):
    if request.method == 'POST':
        pub_instance = Publication.objects.get(id=pubid)
        if not request.user.id == pub_instance.submitter.id:
            entries = Publication.objects.filter(submitter=request.user.id)
            error = 'Error: You must be the owner of a submission to edit it.'
            return render(request, 'site/review.html', {'message': None, 'entries': entries, 'error': error})

        pub_form = PublicationForm(request.POST or None, instance=pub_instance)
        AuthorFormSet = modelformset_factory(Author, form=AuthorForm, can_delete=True)
        author_form_set = AuthorFormSet(request.POST, queryset=pub_instance.authors.all())
        pub_type = int(request.POST.get('pub_type', ''))
        if pub_type == 0:  # book
            bookinstance = Book.objects.get(publication_id=pub_instance)
            media_form = BookForm(request.POST or None, instance=bookinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                book = media_form.save(commit=False)
                book.publication_id = publication
                book.save()
                return redirect('review')
        elif pub_type == 1:  # conference
            conferenceinstance = Conference.objects.get(publication_id=pub_instance)
            media_form = ConferenceForm(request.POST or None, instance=conferenceinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                conference = media_form.save(commit=False)
                conference.publication_id = publication
                conference.save()
                return redirect('review')
        elif pub_type == 2:  # journal
            journalinstance = Journal.objects.get(publication_id=pub_instance)
            media_form = JournalForm(request.POST or None, instance=journalinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                journal = media_form.save(commit=False)
                journal.publication_id = publication
                journal.save()
                return redirect('review')
        elif pub_type == 3:  # magazine
            magazineinstance = Magazine.objects.get(publication_id=pub_instance)
            media_form = MagazineForm(request.POST or None, instance=magazineinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                magazine = media_form.save(commit=False)
                magazine.publication_id = publication
                magazine.save()
                return redirect('review')
        elif pub_type == 4:  # poster
            posterinstance = Poster.objects.get(publication_id=pub_instance)
            media_form = PosterForm(request.POST or None, instance=posterinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                poster = media_form.save(commit=False)
                poster.publication_id = publication
                poster.save()
                return redirect('review')
        elif pub_type == 5:  # presentation
            presentationinstance = Book.objects.get(publication_id=pub_instance)
            media_form = PresentationForm(request.POST or None, instance=presentationinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                presentation = media_form.save(commit=False)
                presentation.publication_id = publication
                presentation.save()
                return redirect('review')
        elif pub_type == 6:  # technical report
            techinstance = TechnicalReport.objects.get(publication_id=pub_instance)
            media_form = TechnicalReportForm(request.POST or None, instance=techinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                techreport = media_form.save(commit=False)
                techreport.publication_id = publication
                techreport.save()
                return redirect('review')
        elif pub_type == 7:  # other
            otherinstance = Other.objects.get(publication_id=pub_instance)
            media_form = OtherForm(request.POST or None, instance=otherinstance)
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, pub_type)
                other = media_form.save(commit=False)
                other.publication_id = publication
                other.save()
                return redirect('review')
        ens = request.POST.getlist('ensemble')
        ensemble_data = str([[index+1, int('0' + str(ens[index]))] for index in range(len(ens)) if ens[index] is not u''])
        return render(request, 'site/edit.html',
                      {'pub_form': pub_form, 'author_form': author_form_set, 'freq_form': FrequencyForm(initial=request.POST), 'exp_form': ExperimentForm(initial=request.POST),
                       'keyword_form': KeywordForm(initial=request.POST),
                       'model_form': ModelForm(initial=request.POST), 'var_form': VariableForm(initial=request.POST), 'media_form': media_form, 'pub_type': pub_type,
                       'ensemble_data': ensemble_data,
                       })

    else:
        publication = Publication.objects.get(id=pubid)
        authors = publication.authors.all()
        userid = request.user.id
        if userid == publication.submitter.id:
            pub_form = PublicationForm(instance=publication)
            AuthorFormSet = modelformset_factory(Author, AuthorForm, extra=0)
            author_form = AuthorFormSet(queryset=authors)
            if publication.publication_type == 0: # book
                media_form = BookForm(instance=Book.objects.get(publication_id=publication))
            elif publication.publication_type == 1: # conference
                media_form = ConferenceForm(instance=Conference.objects.get(publication_id=publication))
            elif publication.publication_type == 2:  # journal
                media_form = JournalForm(instance=Journal.objects.get(publication_id=publication))
            elif publication.publication_type == 3:  # magazine
                media_form = MagazineForm(instance=Magazine.objects.get(publication_id=publication))
            elif publication.publication_type == 4:  # poster
                media_form = PosterForm(instance=Poster.objects.get(publication_id=publication))
            elif publication.publication_type == 5:  # presentation
                media_form = PresentationForm(instance=Presentation.objects.get(publication_id=publication))
            elif publication.publication_type == 6:  # technical report
                media_form = TechnicalReportForm(instance=TechnicalReport.objects.get(publication_id=publication))
            elif publication.publication_type == 7:  # other
                media_form = OtherForm(instance=Other.objects.get(publication_id=publication))
            freq_form = FrequencyForm(initial={'frequency': [box.id for box in publication.frequency.all()]})
            exp_form = ExperimentForm(initial={'experiment': [box.id for box in publication.experiments.all()]})
            keyword_form = KeywordForm(initial={'keyword': [box.id for box in publication.keywords.all()]})
            model_form = ModelForm(initial={'model': [box.id for box in publication.model.all()]})
            var_form = VariableForm(initial={'variable': [box.id for box in publication.variables.all()]})
            ensemble_data = str([[value['experiment_id'], value['ensemble']] for value in
                             PubModels.objects.filter(publication_id=publication.id).values('experiment_id', 'ensemble')])
            return render(request, 'site/edit.html',
                          {'pub_form': pub_form, 'author_form': author_form, 'freq_form': freq_form, 'exp_form': exp_form, 'keyword_form': keyword_form,
                           'model_form': model_form, 'var_form': var_form, 'media_form': media_form, 'pub_type': publication.publication_type,
                           'ensemble_data': ensemble_data,
                           })
        else:
            entries = Publication.objects.filter(submitter=userid)
            error = 'Error: You must be the owner of a submission to edit it.'
            return render(request, 'site/review.html', {'message': None, 'entries': entries, 'error': error})


@login_required()
def new(request):
    if request.method == 'GET':
        return render(request, 'site/new_publication.html')
    elif request.method == 'POST':
        pub_form = PublicationForm(request.POST, prefix='pub')
        pub_type = request.POST.get('pub_type', '')
        AuthorFormSet = formset_factory(AuthorForm)
        author_form_set = AuthorFormSet(request.POST)
        if pub_type == 'Book':
            media_form = BookForm(request.POST, prefix='book')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 0)
                book = media_form.save(commit=False)
                book.publication_id = publication
                book.save()
                return HttpResponse(status=200)
        elif pub_type == 'Conference':
            media_form = ConferenceForm(request.POST, prefix='conf')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 1)
                conference = media_form.save(commit=False)
                conference.publication_id = publication
                conference.save()
                return HttpResponse(status=200)
        elif pub_type == 'Journal':
            media_form = JournalForm(request.POST, prefix='journal')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 2)
                journal = media_form.save(commit=False)
                journal.publication_id = publication
                journal.save()
                return HttpResponse(status=200)
        elif pub_type == 'Magazine':
            media_form = MagazineForm(request.POST, prefix='mag')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 3)
                magazine = media_form.save(commit=False)
                magazine.publication_id = publication
                magazine.save()
                return HttpResponse(status=200)
        elif pub_type == 'Poster':
            media_form = PosterForm(request.POST, prefix='poster')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 4)
                poster = media_form.save(commit=False)
                poster.publication_id = publication
                poster.save()
                return HttpResponse(status=200)
        elif pub_type == 'Presentation':
            media_form = PresentationForm(request.POST, prefix='pres')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 5)
                presentation = media_form.save(commit=False)
                presentation.publication_id = publication
                presentation.save()
                return HttpResponse(status=200)
        elif pub_type == 'Technical_Report':
            media_form = TechnicalReportForm(request.POST, prefix='tech')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 6)
                techreport = media_form.save(commit=False)
                techreport.publication_id = publication
                techreport.save()
                return HttpResponse(status=200)
        elif pub_type == 'Other':
            media_form = OtherForm(request.POST, prefix='other')
            if media_form.is_valid() and pub_form.is_valid() and author_form_set.is_valid():
                publication = save_publication(pub_form, request, author_form_set, 7)
                other = media_form.save(commit=False)
                other.publication_id = publication
                other.save()
                return HttpResponse(status=200)
        pub_form = str(pub_form.as_p()).replace('<p>', '')
        pub_form = pub_form.replace('</p>', '')
        media_form = str(media_form.as_p()).replace('<p>', '')
        media_form = media_form.replace('</p>', '')
        author_form_set = str(author_form_set.as_p()).replace('<p>', '')
        author_form_set = author_form_set.replace('</p>', '')
        return JsonResponse({'pub_form': pub_form, 'media_form': media_form, 'auth_form': author_form_set},
                            status=400)  # These should be strings actually


def finddoi(request):
    doi = request.GET.get('doi')
    if not doi or doi.isspace():
        empty = True
    else:
        empty = False
        accept = 'application/vnd.citationstyles.csl+json; locale=en-US'
        headers = {'accept': accept}
        if doi[:5].lower() == 'doi: ':  # grabs first 5 characters lowercases, and compares
            try:
                url = "http://dx.doi.org/" + doi.split()[1]  # removes "doi:" and whitespace leaving only the doi
            except IndexError:
                return (doi.strip('\n') + " -- Invalid DOI.\n")
        elif doi.startswith('doi:10'):
            url = "http://dx.doi.org/" + doi[4:]  # remove 'doi:'
        elif doi.startswith("http://dx.doi.org/"):
            url = doi
        else:
            url = "http://dx.doi.org/" + doi
        r = requests.get(url, headers=headers)
    if not empty and r.status_code == 200:

        # TODO: Catch differences between agencies e.g. Crossref vs DataCite
        initial = r.json()
        if 'DOI' in initial.keys():
            doi = initial['DOI']
        else:
            doi = ''
        if 'ISBN' in initial.keys():
            isbn = initial['ISBN']
        else:
            isbn = ''
        if 'title' in initial.keys():
            title = initial['title']
        else:
            title = ''
        if 'URL' in initial.keys():
            url = requests.get(initial['URL'], stream=True, verify=False).url  # use llnl cert instead of verify=False
        else:
            url = ''
        if 'page' in initial.keys():
            page = initial['page']
        else:
            page = ''
        if 'publisher' in initial.keys():
            publisher = initial['publisher']
        else:
            publisher = ''
        if 'published-print' in initial.keys():
            publication_date = initial['published-print']['date-parts'][0][0]
        else:
            publication_date = ''
        if 'author' in initial.keys():
            authors_list = []
            AuthorFormSet = formset_factory(AuthorForm, extra=0)
            if 'given' in initial['author'][0].keys():
                for author in initial['author']:
                    authors_list.append({'first_name': author['given'], 'last_name': author['family']})
                author_form = AuthorFormSet(initial=authors_list)
            elif 'literal' in initial['author'][0].keys():
                for author in initial['author']:
                    authors_list.append({'first_name': author['literal']})
                author_form = AuthorFormSet(initial=authors_list)
            else:
                AuthorFormSet = formset_factory(AuthorForm, extra=1)
                author_form = AuthorFormSet()
        else:
            AuthorFormSet = formset_factory(AuthorForm, extra=1)
            author_form = AuthorFormSet()

        init = {'doi': doi, 'isbn': isbn, 'title': title, 'url': url, 'page': page, 'publisher': publisher,
                'publication_date': publication_date}
        pub_form = PublicationForm(prefix='pub', initial=init)
        book_form = BookForm(prefix='book', initial={'publisher': publisher, 'publication_date': publication_date})
        conference_form = ConferenceForm(prefix='conf')
        journal_form = JournalForm(prefix='journal')
        magazine_form = MagazineForm(prefix='mag')
        poster_form = PosterForm(prefix='poster')
        presentation_form = PresentationForm(prefix='pres')
        technical_form = TechnicalReportForm(prefix='tech')
        other_form = OtherForm(prefix='other')
        exp_form = ExperimentForm()
        freq_form = FrequencyForm()
        keyword_form = KeywordForm()
        model_form = ModelForm()
        var_form = VariableForm()
        return render(request, 'site/publication_details.html',
                      {'pub_form': pub_form, 'author_form': author_form,
                       'book_form': book_form,
                       'conference_form': conference_form,
                       'journal_form': journal_form, 'magazine_form': magazine_form, 'poster_form': poster_form,
                       'presentation_form': presentation_form, 'technical_form': technical_form,
                       'other_form': other_form, 'exp_form': exp_form, 'freq_form': freq_form,
                       'keyword_form': keyword_form, 'model_form': model_form, 'var_form': var_form})
    else:
        pub_form = PublicationForm(prefix='pub')
        AuthorFormSet = formset_factory(AuthorForm, extra=1)
        author_form = AuthorFormSet()
        book_form = BookForm(prefix='book')
        conference_form = ConferenceForm(prefix='conf')
        journal_form = JournalForm(prefix='journal')
        magazine_form = MagazineForm(prefix='mag')
        poster_form = PosterForm(prefix='poster')
        presentation_form = PresentationForm(prefix='pres')
        technical_form = TechnicalReportForm(prefix='tech')
        other_form = OtherForm(prefix='other')
        exp_form = ExperimentForm()
        freq_form = FrequencyForm()
        keyword_form = KeywordForm()
        model_form = ModelForm()
        var_form = VariableForm()
        return render(request, 'site/publication_details.html',
                      {'pub_form': pub_form, 'author_form': author_form, 'book_form': book_form,
                       'conference_form': conference_form,
                       'journal_form': journal_form, 'magazine_form': magazine_form, 'poster_form': poster_form,
                       'presentation_form': presentation_form, 'technical_form': technical_form,
                       'other_form': other_form, 'exp_form': exp_form, 'freq_form': freq_form,
                       'keyword_form': keyword_form, 'model_form': model_form, 'var_form': var_form,
                       'message': 'Unable to pre-fill form with the given DOI'})


# ajax
def ajax(request):
    return HttpResponseRedirect("/search?type='all'")


def ajax_citation(request, pub_id):
    pub = Publication.objects.get(id=pub_id)
    citation =  pub.title + ". " + str(pub.publication_date) + ". " + pub.url
    authors = ", ".join(["{author.title}. {author.last_name}, {author.first_name} {author.middle_name}".format(author=author) for author in pub.authors.all()])
    citation = authors + ": " + citation
    json = "{\"key\": \"" + citation + "\"}"
    return HttpResponse(json)

def ajax_more_info(request, pub_id):
    pub = Publication.objects.get(id=pub_id)

    experiments = ",".join(["{experiments.experiment}".format(experiments=experiments) for experiments in pub.experiments.all()])
    model = ",".join(["{model.model}".format(model=model) for model in pub.model.all()])
    variables = ",".join(["{variables.variable}".format(variables=variables) for variables in pub.variables.all()])
    keywords = ",".join(["{keywords.keyword}".format(keywords=keywords) for keywords in pub.keywords.all()])
    # frequency = ",".join(["{frequency.frequency}".format(frequency=frequency) for frequency in pub.frequency.all()])
    # tags = ",".join(["{tags.name}".format(tags=tags) for tags in pub.tags.all()])

    moreinfo = experiments + "|" + model + "|" + variables + "|" + keywords
    json = "{\"key\": \"" + moreinfo + "\"}"
    return HttpResponse(json)
